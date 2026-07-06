@echo off
chcp 65001 >nul
title Mishu - Obsidian AI Agent
cd /d C:\AI\√ÿ È
echo.
echo ============================================
echo     Mishu - Obsidian AI Agent
echo     Starting, please wait...
echo ============================================
echo.
echo Vault: tian_shu_vault
echo URL:   http://127.0.0.1:7860
echo.
set PYTHONIOENCODING=utf-8
C:\AI\.venv\Scripts\python.exe mishu.py
pause
