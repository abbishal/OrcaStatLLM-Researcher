#!/bin/bash

install_package() {
    PACKAGE=$1
    sudo apt-get install -y $PACKAGE
    if [ $? -ne 0 ]; then
        sudo apt-get install -y --fix-missing $PACKAGE
    fi
}

sudo apt-get update

PACKAGES=(
    build-essential
    libpq-dev
    curl
    libnss3
    libnspr4
    libdbus-1-3
    libcups2
    libxcomposite1
    libxdamage1
    libxext6
    libxfixes3
    libxrandr2
    libgbm1
    libxkbcommon0
    libcairo2
    libasound2
    libasound2-dev
    libatspi2.0-0
    libpangocairo-1.0-0
    libpangoft2-1.0-0
    libgdk-pixbuf2.0-0
    libgdk-pixbuf-xlib-2.0-0
)

for PACKAGE in "${PACKAGES[@]}"; do
    install_package $PACKAGE
done

sudo pip install playwright --break-system-packages
playwright install chromium

pip install --upgrade -r requirements.txt --break-system-packages

pip install --upgrade python-docx --break-system-packages

sudo pip install weasyprint --break-system-packages
if [ $? -ne 0 ]; then
    sudo apt-get install -y libjpeg-dev libpq-dev libxml2-dev libxslt-dev
    sudo pip install weasyprint --break-system-packages
fi
