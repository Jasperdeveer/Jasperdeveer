@echo off
:: Spam Uitschrijver — startscript voor Windows
cd /d "%~dp0"

python -c "import flask" 2>nul
if errorlevel 1 (
    echo Dependencies installeren...
    pip install -r requirements.txt
)

if not exist ".env" (
    echo.
    echo  Geen .env bestand gevonden.
    echo  Kopieer .env.example naar .env en vul je gegevens in.
    echo  Zie de setup-pagina voor instructies.
    echo.
    pause
    exit /b 1
)

echo.
echo  Spam Uitschrijver wordt gestart...
echo  Open je Tailscale-adres in Safari op je iPhone.
echo  Druk Ctrl+C om te stoppen.
echo.

gunicorn app:app --bind 127.0.0.1:5000 --workers 1 --timeout 60
pause
