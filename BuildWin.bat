Clear.bat
cp main.py launcher_win.py
python -m PyInstaller --onefile --windowed --noconsole --icon=mcsmanager-launcher.ico launcher_win.py
python -m PyInstaller --onefile --windowed --noconsole --icon=mcsmanager-launcher.ico installer_updater.py
python -m PyInstaller --onefile --windowed --noconsole --icon=mcsmanager-launcher.ico start.py
echo 1.0.1 > version_win_launcher.txt