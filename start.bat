@echo off
chcp 65001 >nul

echo.
echo ====================================
echo   Second Cerveau - Demarrage
echo ====================================
echo.

:: Lire les variables depuis .env
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0.env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

:: Bot Telegram
if defined TELEGRAM_BOT_TOKEN (
    if not "%TELEGRAM_BOT_TOKEN%"=="optionnel_colle_ton_token_ici" (
        start "Second Cerveau - Telegram" cmd /k "cd /d %~dp0 && python -X utf8 bot_telegram.py"
        echo [OK] Bot Telegram lance
    ) else (
        echo [--] Bot Telegram : token non configure dans .env
    )
) else (
    echo [--] Bot Telegram : TELEGRAM_BOT_TOKEN absent du .env
)

:: Watchdog inbox
if exist "%~dp0inbox" (
    start "Second Cerveau - Watchdog" cmd /k "cd /d %~dp0 && python -X utf8 watchdog_capture.py"
    echo [OK] Watchdog lance ^(surveille inbox/^)
)

:: Ouvrir Obsidian
if exist "%LOCALAPPDATA%\Obsidian\Obsidian.exe" (
    start "" "%LOCALAPPDATA%\Obsidian\Obsidian.exe"
    echo [OK] Obsidian ouvert
) else (
    echo [--] Obsidian non trouve ^(ouvre-le manuellement^)
)

echo.
echo ====================================
echo   Recap
echo ====================================
echo   Fiches   ^> %~dp0fiches\
echo   Inbox    ^> %~dp0inbox\
echo   Capture  ^> python capture.py "URL ou texte"
echo ====================================
echo.
echo Ferme cette fenetre pour tout arreter.
echo.
pause
