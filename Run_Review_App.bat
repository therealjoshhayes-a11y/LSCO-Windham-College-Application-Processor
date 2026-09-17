@echo off
cd /d "%~dp0"

echo Starting LSCO TDCJ Review App...
echo.

call .venv\Scripts\activate.bat

start http://127.0.0.1:5000

python scripts\run_review_app.py

echo.
echo Review app stopped.
pause