@echo off
echo ========================================
echo   OPTIMISEUR DE TOURNEES - BOITES A HABITS
echo ========================================
echo.

echo Installation des dependances...
pip install -r requirements.txt

echo.
echo Demarrage de l'application web...
echo Ouvrez votre navigateur sur: http://localhost:5000
echo.

python app.py

pause
