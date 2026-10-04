#!/usr/bin/env bash
set -e

echo "========================================================"
echo "  TIKTOK AUTO DM PRO - LINUX VPS SETUP"
echo "========================================================"

if [ ! -d ".venv" ]; then
    echo "[1/3] Membuat virtual environment .venv..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment .venv sudah ada."
fi

source .venv/bin/activate

echo "[2/3] Menginstall dependencies Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] Menginstall Playwright Chromium & dependencies OS..."
playwright install --with-deps chromium

echo "========================================================"
echo "  INSTALASI VPS SELESAI!"
echo "  Jalankan bot dengan: ./run.sh"
echo "========================================================"
