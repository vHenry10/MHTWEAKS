@echo off
echo Building MHTWEAKS.exe...
pip install pyinstaller pynput pywin32
pyinstaller --onefile --noconsole --name MHTWEAKS mhtweaks.py
echo.
echo Done! MHTWEAKS.exe is in the dist\ folder.
pause
