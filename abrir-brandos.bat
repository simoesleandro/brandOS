@echo off
cd /d "%~dp0"
echo Iniciando o BrandOS Web Console...
python -m app.web.server
pause
