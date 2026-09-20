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
        # 1. Appel de la page de recherche avec ZenRows
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true&premium_proxy=true&wait_for=wc-plp-layout"
        response = requests.get(zenrows_url, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur ZenRows recherche")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 2. Règle stricte : Chercher le lien contenant l'EAN
        product_link = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            if ean in href:
                product_link = href
                break

        # Fallback de sélection si l'EAN n'est pas directement dans l'URL du lien
        if not product_link:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.endswith('.html') and '-' in href:
                    if any(ex in href for ex in ['/liseuse', 'liseuse-', 'ebook', 'univers-', 'promotions', 'livre-occasion', 'coups-de-coeur', 'meilleures-ventes', 'nouveautes', 'precommandes', 'enfants', '/search']):
                        continue
                    filename = href.split('/')[-1]
                    if len(filename) > 20:
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

        # 4. Extraction robuste via JSON-LD sur la page finale
        json_lds = soup.find_all('script', type='application/ld+json')
        for script in json_lds:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ["Book", "Product"] or "name" in item:
                        item_name = item.get("name")
                        if title == "Titre non trouvé" and item_name and item_name not in ["Cultura", "Résultats de recherche", "Livre"]:
                            title = item_name
                        
                        # Extraction robuste de l'image (chaîne de caractères, liste ou dictionnaire)
                        if not cover_url:
                            img_data = item.get("image")
                            if isinstance(img_data, list) and len(img_data) > 0:
                                cover_url = img_data[0] if isinstance(img_data[0], str) else img_data[0].get("url", "")
                            elif isinstance(img_data, dict):
                                cover_url = img_data.get("url", "")
                            elif isinstance(img_data, str):
                                cover_url = img_data

                        # Extraction robuste de la date
                        if date_commercialisation == "Inconnue":
                            for d_key in ["releaseDate", "datePublished", "dateCreated"]:
                                if item.get(d_key):
                                    date_commercialisation = item.get(d_key)
                                    break
            except Exception:
                continue

        # Fallbacks par balises Meta si le JSON-LD n'a pas tout suffi
        if title == "Titre non trouvé":
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                content = og_title['content']
                if content not in ["Résultats de recherche", "Cultura", "Livre"]:
                    title = content

        if not cover_url:
            for meta_attr in [{"property": "og:image"}, {"name": "twitter:image"}]:
                og_image = soup.find('meta', attrs=meta_attr)
                if og_image and og_image.get('content'):
                    cover_url = og_image['content']
                    break

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
