import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright

app = FastAPI()

# Autoriser les requêtes CORS pour que ton application web puisse parler au serveur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
),

@app.get("/")
def home():
    return {"status": "Server is running"}

@app.get("/scrape")
async def scrape_book(ean: str):
    async with async_playwright() as p:
        # Lancement de Chromium en mode headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # URL de recherche (à adapter selon le site cible)
            search_url = f"https://www.google.com/search?q={ean}"
            await page.goto(search_url, timeout=30000)
            
            # Exemple de logique de récupération (à affiner selon la cible)
            title = await page.title()
            
            await browser.close()
            return {"ean": ean, "title": title, "cover": ""}
        except Exception as e:
            await browser.close()
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
