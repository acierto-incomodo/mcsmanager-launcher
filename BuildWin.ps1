./Clear.ps1
cp main.py launcher_win.py
python -m PyInstaller --onefile --windowed --noconsole --icon=mcsmanager-launcher.ico launcher_win.py
python -m PyInstaller --onefile --windowed --noconsole --icon=mcsmanager-launcher.ico installer_updater.py
echo 1.0.0 > version_win_launcher.txt