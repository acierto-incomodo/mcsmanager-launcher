import subprocess
import time
import sys
from pathlib import Path

# Este script replica la funcionalidad del archivo batch para iniciar MCSManager.

# set BASE_DIR=%cd%
BASE_DIR = Path.cwd()

# set DAEMON_DIR=%BASE_DIR%\daemon
DAEMON_DIR = BASE_DIR / "daemon"
# set WEB_DIR=%BASE_DIR%\web
WEB_DIR = BASE_DIR / "web"

# En Windows, usa CREATE_NEW_CONSOLE para ejecutar procesos en nuevas ventanas,
# de forma similar al comando 'start' en un archivo batch.
creation_flags = 0
if sys.platform == "win32":
    creation_flags = subprocess.CREATE_NEW_CONSOLE

# if exist "%DAEMON_DIR%" (
if DAEMON_DIR.is_dir():
    # cd /d "%DAEMON_DIR%"
    # start node_app.exe --enable-source-maps --max-old-space-size=8192 app.js
    print(f"Iniciando proceso Daemon en {DAEMON_DIR}...")
    subprocess.Popen(
        [str(DAEMON_DIR / "node_app.exe"), "--enable-source-maps", "--max-old-space-size=8192", "app.js"],
        cwd=DAEMON_DIR,
        creationflags=creation_flags
    )

# ping localhost (usado como un pequeño retraso)
time.sleep(1)

# if exist "%WEB_DIR%" (
if WEB_DIR.is_dir():
    # cd /d "%WEB_DIR%"
    # start node_app.exe --enable-source-maps --max-old-space-size=8192 app.js --open
    print(f"Iniciando proceso Web en {WEB_DIR}...")
    subprocess.Popen(
        [str(WEB_DIR / "node_app.exe"), "--enable-source-maps", "--max-old-space-size=8192", "app.js"],
        cwd=WEB_DIR,
        creationflags=creation_flags
    )
    
# if exist "%WEB_DIR%" con abrir pagina web (
# if WEB_DIR.is_dir():
    # cd /d "%WEB_DIR%"
    # start node_app.exe --enable-source-maps --max-old-space-size=8192 app.js --open
    # print(f"Iniciando proceso Web en {WEB_DIR}...")
    # subprocess.Popen(
        # [str(WEB_DIR / "node_app.exe"), "--enable-source-maps", "--max-old-space-size=8192", "app.js", "--open"],
        # cwd=WEB_DIR,
        # creationflags=creation_flags
    # )