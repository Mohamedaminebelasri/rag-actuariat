@echo off
title Corpus SFCR - Installation et demarrage
echo ==========================================
echo   Corpus SFCR - Setup Frontend Ivory
echo ==========================================
echo.

cd /d "C:\Users\PC\Documents\rag-actuariat\frontend"

echo [1/2] Installation des dependances npm...
call npm install
if errorlevel 1 (
    echo ERREUR: npm install a echoue
    pause
    exit /b 1
)
echo.
echo [2/2] Demarrage du serveur de developpement...
echo Le site sera accessible sur http://localhost:3000
echo.
start "" "http://localhost:3000/chat"
call npm run dev
pause
