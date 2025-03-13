#!/bin/bash

sudo apt-get update && sudo apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    
sudo pip install playwright
playwright install chromium

pip install --upgrade -r requirements.txt
pip install --upgrade python-docx
sudo pip install weasyprint
