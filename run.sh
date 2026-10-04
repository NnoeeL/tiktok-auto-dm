#!/usr/bin/env bash
echo "========================================================"
echo "  MENJALANKAN TIKTOK AUTO DM PRO (VPS / SERVER)"
echo "  Dashboard: http://<IP_SERVER_ANDA>:8000"
echo "========================================================"

if [ ! -f ".venv/bin/python" ]; then
    echo "Virtual environment belum siap. Menjalankan ./setup.sh..."
    bash setup.sh
fi

source .venv/bin/activate
python main.py
