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
    try:
        zenrows_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_API_KEY}&url={target_url}&js_render=true&premium_proxy=true"
        response = requests.get(zenrows_url, timeout=60)
        
        html_content = response.text
        
        # On vérifie si l'EAN est présent dans le HTML renvoyé
        ean_present = ean in html_content
        # On cherche s'il y a un bloc de données react ou json-ld
        has_json_ld = "application/ld+json" in html_content
        
        return {
            "status_code": response.status_code,
            "html_length": len(html_content),
            "ean_found_in_html": ean_present,
            "has_json_ld": has_json_ld,
            # On extrait un morceau un peu plus loin dans le texte (par exemple du caractère 5000 à 7000)
            "html_middle_snippet": html_content[5000:7000] if len(html_content) > 7000 else "Page trop courte"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    importuvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
