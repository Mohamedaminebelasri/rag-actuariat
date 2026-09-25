@echo off
title Corpus SFCR - Installation et Lancement
cd /d "C:\Users\PC\Documents\rag-actuariat\frontend"

echo ============================================
echo   Corpus SFCR - Installation et Lancement
echo ============================================
echo.

echo [1/4] Verification de Node.js...
node --version
if %errorlevel% neq 0 (
    echo ERREUR: Node.js n'est pas installe!
    echo Telechargez Node.js depuis https://nodejs.org
    pause
    exit /b 1
)
echo.

echo [2/4] Suppression de l'ancien node_modules...
if exist node_modules (
    rmdir /s /q node_modules
)
if exist .next (
    rmdir /s /q .next
)
if exist package-lock.json (
    del package-lock.json
)
echo Fait.
echo.

echo [3/4] Installation des dependances (npm install)...
echo Cela peut prendre 1-2 minutes...
npm install
if %errorlevel% neq 0 (
    echo ERREUR: npm install a echoue!
    pause
    exit /b 1
)
echo.

echo [4/4] Lancement du serveur de developpement...
echo.
echo ============================================
echo   Le site sera accessible sur:
echo   http://localhost:3000
echo ============================================
echo.
echo Ouvrez Chrome et allez sur http://localhost:3000
echo Pour arreter le serveur, fermez cette fenetre.
echo.
npm run dev
pause
