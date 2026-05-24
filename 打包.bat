@echo off

title RocoCaptureV2 Build

cd /d "D:\Code\PythonProject\RocoCaptureV2"

call ".venv\Scripts\activate.bat"

pyinstaller "RocoCaptureV2.spec"

echo.
echo ==============================
echo Okay!
echo ==============================

pause