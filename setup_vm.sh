#!/bin/bash
# ============================================================
# Setup script for GCP Ubuntu VM (e2-medium, Milan)
# Run once after VM creation:  bash setup_vm.sh
# ============================================================
set -e

echo "=== [1/6] Aggiornamento sistema ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== [2/6] Installazione dipendenze sistema ==="
sudo apt-get install -y \
    python3 python3-pip python3-venv git \
    wget gnupg curl unzip \
    python3-tk python3-dev xvfb \
    libnss3 libxss1 libatk-bridge2.0-0 libgtk-3-0 \
    libdrm2 libxcomposite1 libxrandr2 libgbm1 libasound2 \
    fonts-liberation x11-utils

echo "=== [3/6] Installazione Google Chrome ==="
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable

echo "=== [4/6] Setup progetto ==="
cd /opt
sudo git clone https://github.com/TUO_ORG/crawl.git adclicker || (cd adclicker && sudo git pull)
sudo chown -R $USER:$USER /opt/adclicker
cd /opt/adclicker

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [5/6] Configurazione servizio systemd ==="
sudo tee /etc/systemd/system/adclicker.service > /dev/null <<EOF
[Unit]
Description=Ad Clicker Loop
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/adclicker
Environment="DISPLAY=:99"
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1920x1080x16 -ac +extension GLX +render -noreset &
ExecStart=/opt/adclicker/venv/bin/python run_in_loop.py
Restart=always
RestartSec=30
StandardOutput=append:/opt/adclicker/logs/service.log
StandardError=append:/opt/adclicker/logs/service.log

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /opt/adclicker/logs

echo "=== [6/6] Avvio servizio ==="
sudo systemctl daemon-reload
sudo systemctl enable adclicker
sudo systemctl start adclicker

echo ""
echo "✅ Setup completato!"
echo "   Controlla stato:  sudo systemctl status adclicker"
echo "   Vedi log:         tail -f /opt/adclicker/logs/adclicker.log"
echo "   Riavvia:          sudo systemctl restart adclicker"
echo "   Ferma:            sudo systemctl stop adclicker"
