@echo off
chcp 65001 > nul
title Telegram Bot 24/7 - Национальный сертификат (Gemini AI)
:loop
cls
echo ========================================================
echo   Telegram-бот: Национальный сертификат (Режим 24/7)
echo   Модель: Google Gemini 3.5 Flash Lite
echo   Статус: ОНЛАЙН
echo ========================================================
python bot.py
echo.
echo [ВНИМАНИЕ] Процесс был прерван. Автоматический перезапуск через 3 секунды...
timeout /t 3 /nobreak > nul
goto loop
