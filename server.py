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
        # 1. Appel de la page de recherche en attendant 'a.one-product' via ZenRows
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true&premium_proxy=true&wait_for=a.one-product"
        response = requests.get(zenrows_url, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur ZenRows recherche")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 2. Récupération directe du lien du premier produit comme dans ton script Playwright
        product_link_el = soup.select_one("a.one-product")
        product_url = product_link_el['href'] if product_link_el and product_link_el.has_attr('href') else None

        if product_url:
            if product_url.startswith('/'):
                target_product_url = f"https://www.cultura.com{product_url}"
            else:
                target_product_url = product_url

            # 3. Navigation directe vers la page produit, en attendant le chargement de la div #new-react-product-details
            prod_zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_product_url}&js_render=true&premium_proxy=true&wait_for=%23new-react-product-details"
            prod_response = requests.get(prod_zenrows_url, timeout=60)
            if prod_response.status_code == 200:
                soup = BeautifulSoup(prod_response.text, 'html.parser')

        # 4. Extraction du JSON interne de la div #new-react-product-details
        react_div = soup.find('div', id='new-react-product-details')
        if react_div and react_div.has_attr('data-graphql-response'):
            try:
                raw_json = react_div['data-graphql-response']
                graphql_data = json.loads(raw_json)
                
                if graphql_data.get('name'):
                    title = graphql_data.get('name')
                
                # Recherche de l'image dans les différentes clés possibles du JSON
                for img_key in ['image', 'cover', 'imageUrl', 'kit_image', 'pictures', 'media']:
                    img_val = graphql_data.get(img_key)
                    if img_val:
                        if isinstance(img_val, str):
                            cover_url = img_val
                            break
                        elif isinstance(img_val, dict):
                            cover_url = img_val.get('url', '') or img_val.get('large', '')
                            if cover_url:
                                break
                        elif isinstance(img_val, list) and len(img_val) > 0:
                            cover_url = img_val[0] if isinstance(img_val[0], str) else img_val[0].get('url', '')
                            break
                
                # Recherche de la date
                for date_key in ['releaseDate', 'datePublished', 'publicationDate', 'created_at']:
                    if graphql_data.get(date_key):
                        date_commercialisation = graphql_data.get(date_key)
                        break
            except Exception as e:
                print("Erreur parsing GraphQL JSON:", str(e))

        # 5. Fallback sur les méta-tags si l'image n'a pas été trouvée dans le JSON
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
