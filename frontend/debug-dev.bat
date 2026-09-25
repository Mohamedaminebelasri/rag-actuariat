@echo off
title Corpus SFCR - Debug
cd /d "C:\Users\PC\Documents\rag-actuariat\frontend"
echo === Verification Node.js ===
node --version
echo.
echo === Verification npm ===
npm --version
echo.
echo === Lancement npm run dev ===
echo.
npm run dev 2>&1
echo.
echo === Le serveur s'est arrete avec le code: %errorlevel% ===
echo.
echo Appuyez sur une touche pour fermer...
pause >nul
