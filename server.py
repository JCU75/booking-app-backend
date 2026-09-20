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

    try:
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true"
        response = requests.get(zenrows_url, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Erreur ZenRows status: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Diagnostic : est-ce qu'on trouve des éléments sur la page ?
        # On va regarder si le titre de la page HTML correspond à quelque chose de cohérent
        page_title_tag = soup.find('title')
        html_title = page_title_tag.text if page_title_tag else "Pas de balise title"

        react_div = soup.select_one("div#new-react-product-details")
        
        # Si pas de react_div direct, testons le premier lien produit
        product_link = soup.select_one("a.one-product")
        product_url_found = product_link.get("href") if product_link else "Aucun a.one-product trouvé"

        return {
            "debug_html_title": html_title,
            "debug_product_url_found": product_url_found,
            "has_react_div": react_div is not None,
            "title": title,
            "cover_url": cover_url,
            "date": date_commercialisation,
            "ean": ean
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    importuvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
