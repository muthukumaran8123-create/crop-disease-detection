@echo off
cd /d "%~dp0"
py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 was not found. Install it from https://www.python.org/downloads/ and select Add Python to PATH.
  pause
  exit /b 1
)
py -3.11 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Install complete. Download/extract PlantVillage and train the model using the README instructions.
pause
exit /b 0
:failed
echo.
echo Installation failed. Read the error above and check README.md for troubleshooting.
pause
exit /b 1
