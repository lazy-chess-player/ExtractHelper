@echo off
echo Starting ExtractHelper GUI...
echo.
echo Please wait for initialization...
echo Once started, your browser should open automatically.
echo If not, please visit: http://localhost:8551
echo.
echo ========================================================
echo   IMPORTANT: DO NOT CLOSE THIS WINDOW WHILE USING THE APP
echo ========================================================
echo.

call .venv\Scripts\activate.bat
python -m app.gui.web_app

pause
