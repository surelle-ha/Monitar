pip install pyinstaller psutil PyQt5 requests
python -m PyInstaller src/main.py --windowed --icon asset/program.ico
copy dist\main\main.exe dist\main\Monitar.exe
del dist\main\main.exe
