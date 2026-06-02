@echo off
title Second Cerveau — Brain System
cd /d "%~dp0"

echo [1/3] Agent de sync...
echo    (Premier lancement: attendre que l'agent ait fini avant d'utiliser l'app)
start "Brain Agent" /MIN python brain_agent.py

echo [2/3] Serveur API (attente 10s)...
timeout /t 10 /nobreak >nul
start "Brain Server" /MIN python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842 --log-level warning

echo [3/3] Interface Electron (attente 3s)...
timeout /t 3 /nobreak >nul
cd brain_app
start "Brain App" npx electron .

echo Brain System demarre !
