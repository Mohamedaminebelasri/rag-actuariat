@echo off
cd /d "C:\Users\PC\Documents\rag-actuariat\frontend"
echo NODE_VERSION: > diagnostic.txt
node --version >> diagnostic.txt 2>&1
echo NPM_VERSION: >> diagnostic.txt
npm --version >> diagnostic.txt 2>&1
echo NODE_PATH: >> diagnostic.txt
where node >> diagnostic.txt 2>&1
echo NEXT_VERSION: >> diagnostic.txt
npx next --version >> diagnostic.txt 2>&1
echo NPM_RUN_DEV_OUTPUT: >> diagnostic.txt
npm run dev >> diagnostic.txt 2>&1
echo EXIT_CODE: %errorlevel% >> diagnostic.txt
exit
