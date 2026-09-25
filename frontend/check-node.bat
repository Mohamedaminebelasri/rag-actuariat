@echo off
title Diagnostic Node.js
echo === DIAGNOSTIC CORPUS SFCR === > "%~dp0diagnostic.log"
echo Date: %date% %time% >> "%~dp0diagnostic.log"
echo. >> "%~dp0diagnostic.log"

echo === Version Node.js === >> "%~dp0diagnostic.log"
node --version >> "%~dp0diagnostic.log" 2>&1
echo. >> "%~dp0diagnostic.log"

echo === Version npm === >> "%~dp0diagnostic.log"
npm --version >> "%~dp0diagnostic.log" 2>&1
echo. >> "%~dp0diagnostic.log"

echo === Chemin Node.js === >> "%~dp0diagnostic.log"
where node >> "%~dp0diagnostic.log" 2>&1
echo. >> "%~dp0diagnostic.log"

echo === Contenu package.json (version next) === >> "%~dp0diagnostic.log"
cd /d "C:\Users\PC\Documents\rag-actuariat\frontend"
type package.json >> "%~dp0diagnostic.log" 2>&1
echo. >> "%~dp0diagnostic.log"

echo === Lancement npm run dev === >> "%~dp0diagnostic.log"
echo Lancement de npm run dev... Patientez...
npm run dev >> "%~dp0diagnostic.log" 2>&1
echo. >> "%~dp0diagnostic.log"
echo === Code de sortie: %errorlevel% === >> "%~dp0diagnostic.log"

echo Diagnostic termine. Voir diagnostic.log
echo Appuyez sur une touche pour fermer...
pause >nul
