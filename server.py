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
    
    title = "Titre non trouvé"
    date_commercialisation = "Inconnue"
    cover_url = ""
    target_product_url = target_url

    try:
        # 1. Appel de la page de recherche
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true&premium_proxy=true"
        response = requests.get(zenrows_url, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur ZenRows recherche")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 2. Chercher un vrai lien produit de manière plus stricte
        product_link = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            # On cherche un lien qui finit par .html mais qui contient des chiffres ou un format de produit (ex: pas juste /livre.html)
            if href.endswith('.html') and '/search' not in href and href != '/livre.html' and ('-' in href or any(char.isdigit() for char in href)):
                # On évite les liens de catégories génériques
                if not any(cat in href for cat in ['/univers-', '/le-magasin', '/aide/', '/evenement']):
                    product_link = href
                    break

        if product_link:
            if product_link.startswith('/'):
                target_product_url = f"https://www.cultura.com{product_link}"
            else:
                target_product_url = product_link

            # 3. Interroger la vraie page produit
            prod_zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_product_url}&js_render=true&premium_proxy=true"
            prod_response = requests.get(prod_zenrows_url, timeout=60)
            if prod_response.status_code == 200:
                soup = BeautifulSoup(prod_response.text, 'html.parser')

        # 4. Extraction via JSON-LD sur la page finale
        json_lds = soup.find_all('script', type='application/ld+json')
        for script in json_lds:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ["Book", "Product"] or "name" in item:
                        if title == "Titre non trouvé" and item.get("name") and item.get("name") not in ["Cultura", "Résultats de recherche"]:
                            title = item.get("name")
                        if not cover_url and item.get("image"):
                            img = item.get("image")
                            cover_url = img[0] if isinstance(img, list) else img
                        if date_commercialisation == "Inconnue" and (item.get("releaseDate") or item.get("datePublished")):
                            date_commercialisation = item.get("releaseDate") or item.get("datePublished")
            except Exception:
                continue

        # Fallbacks ciblés
        if title == "Titre non trouvé":
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content') and og_title['content'] not in ["Résultats de recherche", "Cultura"]:
                title = og_title['content']

        if not cover_url:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                cover_url = og_image['content']

        if date_commercialisation != "Inconnue" and len(date_commercialisation) >= 10:
            date_commercialisation = date_commercialisation[:10]

        return {
            "title": title,
            "cover_url": cover_url,
            "date": date_commercialisation,
            "ean": ean,
            "resolved_url": target_product_url
        }

    except Exception as e:
        print("-> ERREUR CRITIQUE :", str(e))
        raise HTTPException(status_code=500, detail=f"Erreur Python : {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
