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
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true&premium_proxy=true"
        response = requests.get(zenrows_url, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur ZenRows")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Recherche des blocs de données structurées JSON-LD
        json_lds = soup.find_all('script', type='application/ld+json')
        for script in json_lds:
            try:
                data = json.loads(script.string)
                # Parfois le JSON-LD est une liste d'objets
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ["Book", "Product"] or "name" in item:
                        if title == "Titre non trouvé" and item.get("name"):
                            title = item.get("name")
                        if not cover_url and item.get("image"):
                            img = item.get("image")
                            cover_url = img[0] if isinstance(img, list) else img
                        if date_commercialisation == "Inconnue" and (item.get("releaseDate") or item.get("datePublished")):
                            date_commercialisation = item.get("releaseDate") or item.get("datePublished")
            except Exception:
                continue

        # Fallback sur les balises og: meta si besoin
        if title == "Titre non trouvé":
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
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
            "ean": ean
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    importuvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
