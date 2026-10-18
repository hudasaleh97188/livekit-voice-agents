@echo off
cd /d "%~dp0"
python -m support_app.launch %*
if errorlevel 1 pause
