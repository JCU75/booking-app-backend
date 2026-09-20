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
    search_url = f"https://www.cultura.com/search/results?search_query={ean}"
    print(f"\n--- RECHERCHE POUR EAN : {ean} ---")

    title = "Titre non trouvé"
    date_commercialisation = "Inconnue"
    cover_url = ""
    product_url = None

    try:
        # ÉTAPE 1 : Récupérer la page de recherche via ZenRows en attendant a.one-product
        zenrows_search_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={search_url}&js_render=true&premium_proxy=true&wait_for=a.one-product"
        response = requests.get(zenrows_search_url, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur ZenRows recherche")

        soup_search = BeautifulSoup(response.text, 'html.parser')

        # Récupération du lien du premier produit (exactement comme dans Playwright)
        product_link_el = soup_search.select_one("a.one-product")
        if product_link_el and product_link_el.has_attr("href"):
            product_url = product_link_el["href"]
            print(f"-> Lien produit détecté : {product_url}")
        else:
            print("-> Attention : Aucun élément 'a.one-product' trouvé sur la page de recherche.")

        # Gestion de l'URL absolue/relative
        if product_url:
            if product_url.startswith("/"):
                product_url = f"https://www.cultura.com{product_url}"
            print(f"-> Navigation directe vers la page produit : {product_url}")
        else:
            # Fallback direct basé sur l'EAN si la recherche échoue
            product_url = f"https://www.cultura.com/search/results?search_query={ean}"

        # ÉTAPE 2 : Récupérer la page produit finale via ZenRows en attendant div#new-react-product-details
        zenrows_product_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={product_url}&js_render=true&premium_proxy=true&wait_for=%23new-react-product-details"
        prod_response = requests.get(zenrows_product_url, timeout=60)
        
        if prod_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur ZenRows page produit")

        soup_prod = BeautifulSoup(prod_response.text, 'html.parser')

        # ÉTAPE 3 : Extraction via le JSON GraphQL de la div (exactement comme ton code)
        react_div = soup_prod.select_one("div#new-react-product-details")
        if react_div and react_div.has_attr("data-graphql-response"):
            try:
                raw_json = react_div["data-graphql-response"]
                data = json.loads(raw_json)

                # 1. Titre
                if "name" in data:
                    title = data["name"]
                elif "product" in data and isinstance(data["product"], dict) and "name" in data["product"]:
                    title = data["product"]["name"]

                # 2. Date de commercialisation
                for k in ["release_date", "releaseDate", "date_parution", "parution"]:
                    if k in data and data[k]:
                        date_commercialisation = str(data[k])
                        break

                if date_commercialisation == "Inconnue" and "product" in data and isinstance(data["product"], dict):
                    for k in ["release_date", "releaseDate", "date_parution", "parution"]:
                        if k in data["product"] and data["product"][k]:
                            date_commercialisation = str(data["product"][k])
                            break

                print(f"-> Extraction réussie -> Titre : {title} | Date : {date_commercialisation}")

            except Exception as json_err:
                print("-> Erreur parsing JSON :", json_err)

        # Nettoyage de la date
        if date_commercialisation != "Inconnue" and len(date_commercialisation) >= 10:
            date_commercialisation = date_commercialisation[:10]

        # 4. Extraction de la jaquette
        img_el = soup_prod.select_one("img.square__img") or soup_prod.select_one(".pdp-gallery img")
        if img_el and img_el.get("src"):
            cover_url = img_el["src"]
        
        # Fallback méta image si l'élément HTML n'est pas trouvé
        if not cover_url:
            og_img = soup_prod.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                cover_url = og_img['content']

        return {
            "title": title,
            "cover_url": cover_url,
            "date": date_commercialisation,
            "ean": ean,
            "resolved_url": product_url
        }

    except Exception as e:
        print("-> ERREUR CRITIQUE :", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
