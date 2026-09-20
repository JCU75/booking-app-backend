import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
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


@app.get("/get-book/{ean}")
def get_cultura_book(ean: str):
    search_url = f"https://www.cultura.com/search/results?search_query={ean}"
    print(f"\n--- RECHERCHE POUR EAN : {ean} ---")

    title = "Titre non trouvé"
    date_commercialisation = "Inconnue"
    cover_url = ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(search_url, timeout=20000)

            product_url = None
            try:
                page.wait_for_selector("a.one-product", timeout=10000)
                product_link_el = page.locator("a.one-product").first
                product_url = product_link_el.get_attribute("href")
                print(f"-> Lien produit détecté : {product_url}")
            except Exception as e:
                print("-> Attention : Aucun élément 'a.one-product' trouvé sur la page de recherche.")

            if product_url:
                if product_url.startswith("/"):
                    product_url = f"https://www.cultura.com{product_url}"

                print(f"-> Navigation directe vers la page produit : {product_url}")
                page.goto(product_url, timeout=20000)
            else:
                try:
                    page.locator("a.one-product").first.click(timeout=5000)
                except:
                    pass

            try:
                page.wait_for_selector("div#new-react-product-details", timeout=15000)
                print("-> Succès : div#new-react-product-details chargée sur la page finale !")
            except Exception:
                print("-> Attention : div#new-react-product-details absente sur cette page.")

            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

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

                    print(f"-> Extraction réussie -> Titre : {title} | Date : {date_commercialisation}")

                except Exception as json_err:
                    print("-> Erreur parsing JSON :", json_err)

            if date_commercialisation != "Inconnue" and len(date_commercialisation) >= 10:
                date_commercialisation = date_commercialisation[:10]

            img_el = soup.select_one("img.square__img") or soup.select_one(".pdp-gallery img")
            if img_el and img_el.get("src"):
                cover_url = img_el["src"]

            browser.close()

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
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
