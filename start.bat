@echo off
chcp 65001 >nul
set PYTHONUTF8=1

echo.
echo ====================================
echo   Second Cerveau - Demarrage
echo ====================================
echo.

:: Bot Telegram
if defined TELEGRAM_BOT_TOKEN (
    if not "%TELEGRAM_BOT_TOKEN%"=="optionnel_colle_ton_token_ici" (
        start "Second Cerveau - Telegram" cmd /k "cd /d %USERPROFILE%\second_cerveau && set PYTHONUTF8=1 && python bot_telegram.py"
        echo [OK] Bot Telegram lance
    ) else (
        echo [--] Bot Telegram : token non configure
    )
) else (
    echo [--] Bot Telegram : TELEGRAM_BOT_TOKEN absent
)

:: Watchdog inbox
if exist "%USERPROFILE%\second_cerveau\inbox" (
    start "Second Cerveau - Watchdog" cmd /k "cd /d %USERPROFILE%\second_cerveau && set PYTHONUTF8=1 && python watchdog_capture.py"
    echo [OK] Watchdog lance ^(surveille inbox/^)
)

:: Ouvrir Obsidian sur le dossier fiches
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
echo   Fiches      ^> %USERPROFILE%\second_cerveau\fiches\
echo   Inbox       ^> %USERPROFILE%\second_cerveau\inbox\
echo   Capture     ^> python capture.py "URL ou texte"
echo ====================================
echo.
echo Ferme cette fenetre pour tout arreter.
echo.
pause
