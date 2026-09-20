FROM python:3.10-slim

WORKDIR /app

# Installation des dépendances système requises par Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libgdk-pixbuf2.0-0 libpango-1.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpangoft2-1.0-0 \
    libxss1 libxtst6 xdg-utils wget curl --no-install-recommends && rm -rf /var/lib/api/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation de Chromium pour Playwright
RUN playwright install chromium

COPY . .

CMD uvicorn server:app --host 0.0.0.0 --port $PORT
