@echo off
echo ========================================================
echo   TIKTOK AUTO DM PRO - INSTALLATION SETUP (WINDOWS)
echo ========================================================
echo.

if not exist .venv (
    echo [1/3] Membuat virtual environment .venv...
    python -m venv .venv
) else (
    echo [1/3] Virtual environment .venv sudah ada.
)

echo [2/3] Menginstall dependencies Python...
.venv\Scripts\pip.exe install -r requirements.txt

echo [3/3] Mengunduh browser Playwright Chromium...
.venv\Scripts\playwright.exe install chromium

echo.
echo ========================================================
echo   INSTALASI SELESAI!
echo   Jalankan bot dengan mengklik ganda 'run.bat'
echo ========================================================
pause
