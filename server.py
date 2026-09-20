import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ZENROWS_API_KEY = os.environ.get("ZENROWS_API_KEY")

@app.get("/get-book/{ean}")
def get_cultura_book(ean: str):
    target_url = f"https://www.cultura.com/search/results?search_query={ean}"
    print(f"\n--- RECHERCHE ZENROWS POUR EAN : {ean} ---")

    title = "Titre non trouvé"
    date_commercialisation = "Inconnue"
    cover_url = ""

    try:
        # Appel via l'API ZenRows avec le rendu JS activé
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true"
        response = requests.get(zenrows_url, timeout=60)
        
        if response.status_code != 200:
            print(f"-> Erreur ZenRows status: {response.status_code}")
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération via ZenRows")

        soup = BeautifulSoup(response.text, 'html.parser')

        react_div = soup.select_one("div#new-react-product-details")
        
        # Si on est sur la page de recherche, on cherche le premier lien produit
        if not react_div:
            product_link = soup.select_one("a.one-product")
            if product_link and product_link.get("href"):
                product_url = product_link["href"]
                if product_url.startswith("/"):
                    product_url = f"https://www.cultura.com{product_url}"
                
                # Second appel pour récupérer la page produit finale
                prod_zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={product_url}&js_render=true"
                prod_response = requests.get(prod_zenrows_url, timeout=35)
                if prod_response.status_code == 200:
                    soup = BeautifulSoup(prod_response.text, 'html.parser')
                    react_div = soup.select_one("div#new-react-product-details")

        if react_div and react_div.has_attr("data-graphql-response"):
            try:
                raw_json = react_div["data-graphql-response"]
                data = json.loads(raw_json)

                if "name" in data:
                    title = data["name"]
                elif "product" in data and isinstance(data["product"], dict) and "name" in data["product"]:
                    title = data["product"]["name"]

                for k in ["release_date", "releaseDate", "date_parution", "parution"]:
                    if k in data and data[k]:
                        date_commercialisation = str(data[k])
                        break

                if date_commercialisation == "Inconnue" and "product" in data and isinstance(data["product"], dict):
                    for k in ["release_date", "releaseDate", "date_parution", "parution"]:
                        if k in data["product"] and data["product"][k]:
                            date_commercialisation = str(data["product"][k])
                            break

                print(f"-> Succès extraction -> Titre : {title}")
            except Exception as json_err:
                print("-> Erreur parsing JSON :", json_err)

        if date_commercialisation != "Inconnue" and len(date_commercialisation) >= 10:
            date_commercialisation = date_commercialisation[:10]

        img_el = soup.select_one("img.square__img") or soup.select_one(".pdp-gallery img")
        if img_el and img_el.get("src"):
            cover_url = img_el["src"]

        return {
            "title": title,
            "cover_url": cover_url,
            "date": date_commercialisation,
            "ean": ean
        }

    except Exception as e:
        print("-> ERREUR CRITIQUE :", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    importuvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
