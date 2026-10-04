@echo off
title TikTok Auto DM Pro Dashboard
echo ========================================================
echo   MENJALANKAN TIKTOK AUTO DM PRO
echo   Dashboard Web: http://localhost:8000
echo ========================================================
echo.

if not exist .venv\Scripts\python.exe (
    echo [PERINGATAN] Virtual environment belum dibuat.
    echo Menjalankan setup otomatis...
    call setup.bat
)

.venv\Scripts\python.exe main.py
pause
