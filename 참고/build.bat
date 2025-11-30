@echo off
echo.
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo Creating application icon...
python create_icon.py

echo.
echo Building the application with PyInstaller...
python -m PyInstaller NumberGame.spec ^
    --noconfirm ^
    --clean

echo.
echo Build finished. Check the 'dist/NumberGame' folder.
pause 