#!/usr/bin/env python3
import sys
import os
import shutil
import zipfile
import json
import subprocess
from pathlib import Path
import time
from threading import Thread

# Filtrar advertencias de dependencias de requests
import warnings
warnings.filterwarnings("ignore", message=".*urllib3.*")

import requests
from PySide6 import QtCore, QtWidgets, QtGui

# ---------------- CONFIG ------------------

LAUNCHER_VERSION = "1.0.6"

# Windows build is split into two parts
BUILD_URL_WIN_PART1 = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/Build.zip"
BUILD_URL_LINUX = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/Build.zip"
START_EXE_URL = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/start.exe"
USER_ZIP_URL = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/user.zip"
VERSION_URL = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/version.txt"
RELEASE_NOTES_URL = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/ReleaseNotes.txt"

EXE_NAME_WIN   = "start.exe"
EXE_NAME_LINUX = "start.exe"

DOWNLOAD_DIR = Path.cwd() / "downloads"
GAME_DIR     = Path.cwd() / "files"
VERSION_FILE = GAME_DIR / "version.txt"
BUILD_DIR    = GAME_DIR / "mcsmanager"
API_KEY_FILE = GAME_DIR / "api_key.txt"
DAEMON_CONFIG_FILE = BUILD_DIR / "daemon" / "data" / "config.json"
WEB_URL = "http://localhost:24444"
DEFAULT_API_KEY = "a601cbad524241d2b672393f30e85773"


DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
GAME_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- Utils -------------------

def download_file(url: str, dest: Path, progress_callback=None, chunk_size=8192):
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    total = resp.headers.get("content-length")
    total = int(total) if total and total.isdigit() else None

    with open(dest, "wb") as f:
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)
            if progress_callback:
                progress_callback(downloaded, total)

    return dest


def are_panel_processes_running():
    """Checks if MCSManager panel processes are already running."""
    if not sys.platform.startswith("win"):
        return False # Simplified for this request, focusing on Windows

    try:
        # Use tasklist on Windows. CREATE_NO_WINDOW flag hides the console.
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq node_app.exe'],
            capture_output=True, text=True,
            creationflags=0x08000000 # CREATE_NO_WINDOW
        )
        # 'node_app.exe' will be in the output if the process is running.
        return 'node_app.exe' in result.stdout.lower()
    except FileNotFoundError:
        print("Warning: tasklist.exe not found. Cannot check for running processes.")
        return False # Assume not running if we can't check
    except Exception as e:
        print(f"An unexpected error occurred while checking processes: {e}")
        return False


def graceful_shutdown():
    """Tries to gracefully stop all running MCSManager instances via API."""
    try:
        if not DAEMON_CONFIG_FILE.exists():
            print("INFO: Daemon config not found, skipping graceful shutdown.")
            return

        api_key = API_KEY_FILE.read_text(encoding="utf-8").strip() if API_KEY_FILE.exists() else ""
        if not api_key:
            # Use default key if file is missing or empty
            api_key = DEFAULT_API_KEY

        with open(DAEMON_CONFIG_FILE, "r", encoding="utf-8") as f:
            daemon_config = json.load(f)
        daemon_id = daemon_config.get("uuid")
        if not daemon_id:
            print("ERROR: Could not find daemonId in config.json.")
            return

        print("Attempting graceful shutdown of instances...")
        headers = {"X-Requested-With": "XMLHttpRequest"}
        
        # 1. Get list of instances
        instances_url = f"{WEB_URL}/api/service/remote_service_instances"
        instances_params = {
            "apikey": api_key,
            "daemonId": daemon_id,
            "page": 1,
            "page_size": 999,
        }
        
        resp = requests.get(instances_url, params=instances_params, headers=headers, timeout=5)
        resp.raise_for_status()
        instances_data = resp.json()

        if instances_data.get("status") != 200:
            print(f"API Error getting instances: {instances_data.get('data')}")
            return

        running_instances = []
        instance_list = instances_data.get("data", {}).get("data", [])
        if not instance_list:
            print("No instances found on daemon.")
            return

        for instance in instance_list:
            if instance.get("status") == 3:  # 3 = running
                running_instances.append(instance.get("instanceUuid"))

        if not running_instances:
            print("No running instances to stop.")
            return

        # 2. Stop each running instance
        print(f"Found {len(running_instances)} running instance(s). Sending stop commands...")
        stop_url = f"{WEB_URL}/api/protected_instance/stop"
        for instance_uuid in running_instances:
            stop_params = {
                "apikey": api_key,
                "daemonId": daemon_id,
                "uuid": instance_uuid,
            }
            requests.get(stop_url, params=stop_params, headers=headers, timeout=5)
            print(f"  - Stop command sent to instance {instance_uuid[:8]}...")
        
        print("Waiting 5 seconds for instances to stop...")
        time.sleep(5)
        print("Graceful shutdown attempt finished.")

    except requests.exceptions.RequestException:
        print("ERROR: Network error contacting MCSManager API. Is the panel running on port 24444?")
    except Exception as e:
        print(f"ERROR during graceful shutdown: {e}")


def kill_running_processes():
    # 1. Attempt graceful shutdown of instances via API
    graceful_shutdown()

    # 2. Force kill the panel's processes
    if not sys.platform.startswith("win"):
        return

    print("Forcibly terminating panel processes (start.exe, node_app.exe)...")
    processes_to_kill = ["start.exe", "node_app.exe"]
    for process_name in processes_to_kill:
        try:
            # Use taskkill to forcefully terminate the process
            # /F for force, /IM for image name.
            subprocess.run(
                ["taskkill", "/F", "/IM", process_name],
                check=False, capture_output=True
            )
        except (FileNotFoundError, Exception):
            # Ignore errors (e.g., taskkill not found, no permissions, process not running)
            pass
    print("Panel processes terminated.")


def clean_old_version(target_dir: Path):
    # Eliminar LICENSE
    p_license = target_dir / "LICENSE"
    if p_license.exists():
        p_license.unlink()

    # Limpiar daemon y web preservando 'data'
    for folder in ["daemon", "web"]:
        p_folder = target_dir / folder
        if p_folder.exists() and p_folder.is_dir():
            for item in p_folder.iterdir():
                if item.name == "data":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()


def extract_zip(zip_path: Path, to_dir: Path):
    to_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(path=to_dir)


def start_game_process():
    if sys.platform.startswith("win"):
        exe = BUILD_DIR / EXE_NAME_WIN
    else:
        exe = BUILD_DIR / EXE_NAME_LINUX

    if not exe.exists():
        raise FileNotFoundError(f"Ejecutable no encontrado:\n{exe}")

    if not sys.platform.startswith("win"):
        exe.chmod(0o755)

    # os.startfile no establece el directorio de trabajo, lo que causa que start.exe falle.
    # Usamos subprocess.Popen y establecemos el 'cwd' al directorio que contiene el ejecutable.
    subprocess.Popen([str(exe)], cwd=str(exe.parent))

# --------------- GUI ----------------------

class LauncherWindow(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCSManager - Launcher")
        self.setMinimumSize(520, 420)
        self.setMaximumSize(520, 420)
        self.setWindowIcon(QtGui.QIcon.fromTheme("applications-games"))

        self.setup_ui()
        self.refresh_version_display()
        self.load_release_notes()

        self.on_check()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("MCSManager")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:bold;")
        layout.addWidget(title)

        self.status = QtWidgets.QLabel("Listo.")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status)

        # botones principales
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_check  = QtWidgets.QPushButton("Buscar actualización")
        self.btn_update = QtWidgets.QPushButton("Actualizar")
        self.btn_start  = QtWidgets.QPushButton("Iniciar panel")

        self.btn_cancel_autostart = QtWidgets.QPushButton("Cancelar inicio")
        self.btn_cancel_autostart.setVisible(False)
        self.btn_cancel_autostart.clicked.connect(self.cancel_autostart)

        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel_autostart)

        layout.addLayout(btn_layout)

        # ------------ NUEVOS BOTONES -------------
        tools_layout = QtWidgets.QHBoxLayout()

        self.btn_open_folder = QtWidgets.QPushButton("Abrir ubicación")
        self.btn_delete_data = QtWidgets.QPushButton("Eliminar datos")
        self.btn_open_web = QtWidgets.QPushButton("Abrir Web")

        tools_layout.addWidget(self.btn_open_folder)
        tools_layout.addWidget(self.btn_delete_data)
        tools_layout.addWidget(self.btn_open_web)

        layout.addLayout(tools_layout)
        # ------------------------------------------

        # barra de progreso
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()
        
        
        # ----- Release notes -----
        self.release_notes_box = QtWidgets.QTextEdit()
        self.release_notes_box.setReadOnly(True)
        self.release_notes_box.setMinimumHeight(100)
        self.release_notes_box.setStyleSheet(
            "padding:6px; font-size:13px;"
        )
        layout.addWidget(self.release_notes_box)


        # versión al fondo
        self.version_display = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.version_display.setStyleSheet("font-weight:bold; font-size:14px; margin-bottom:8px;")
        layout.addWidget(self.version_display)
        # version_layout = QtWidgets.QHBoxLayout()
        
        # self.version_display = QtWidgets.Qlabel("", alignment=QtCore.Qt.AlingCenter)
        # self.version_display.setStyleSheet("font-weight:bold; font-size:14px;")
        
        # self.launcher_version_label = QtWidgets.QLabel(f"Launcher v{LAUNCHER_VERSION}")
        # self.launcher_version_label.setStyleSheet("font-size:14px; color: gray; margin-left:10px;")
        
        # version_layout.addStretch()
        # version_layout.addWidget(self.version_display)
        # version_layout.addWidget(self.launcher_version_label)
        # version_layout.addStretch()
        
        # layout.addLayout(version_layout)

        # señales
        self.btn_check.clicked.connect(self.on_check)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_start.clicked.connect(self.on_start)

        # nuevas señales
        self.btn_open_folder.clicked.connect(self.open_location)
        self.btn_delete_data.clicked.connect(self.delete_data)
        self.btn_open_web.clicked.connect(self.open_web)

        self.btn_update.setEnabled(False)

    def set_status(self, text):
        self.status.setText(text)

    def refresh_version_display(self):
        if VERSION_FILE.exists():
            try:
                content = VERSION_FILE.read_text(encoding="utf-8").strip()
                self.version_display.setText(content or "Necesitas descargar el panel")
            except:
                self.version_display.setText("Necesitas descargar el panel")
        else:
            self.version_display.setText("Necesitas descargar el panel")

    # ------------ NUEVA FUNCIÓN: ABRIR UBICACIÓN ------------

    def open_location(self):
        folder = str(Path.cwd())
        if sys.platform.startswith("win"):
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    # ------------ NUEVA FUNCIÓN: ABRIR WEB ------------

    def open_web(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://localhost:23333"))

    # ------------ NUEVA FUNCIÓN: ELIMINAR DATOS ------------

    def delete_data(self):
        # Cerrar procesos antes de eliminar para evitar errores de "archivo en uso"
        self.set_status("Cerrando procesos existentes...")
        kill_running_processes()
        # Dar un momento para que los procesos terminen
        time.sleep(2)

        try:
            if DOWNLOAD_DIR.exists():
                shutil.rmtree(DOWNLOAD_DIR)
            if GAME_DIR.exists():
                shutil.rmtree(GAME_DIR)

            DOWNLOAD_DIR.mkdir(exist_ok=True)
            GAME_DIR.mkdir(exist_ok=True)

            self.refresh_version_display()
            self.set_status("Carpetas eliminadas.")

        except Exception as e:
            self.set_status(f"Error: {e}")

    # ------------ CHECK ----------

    def on_check(self):
        self.set_status("Comprobando versión remota...")
        self.btn_check.setEnabled(False)
        Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        try:
            resp = requests.get(VERSION_URL, timeout=30)
            resp.raise_for_status()
            latest = resp.text.strip()
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self, "on_check_failed",
                                            QtCore.Qt.QueuedConnection,
                                            QtCore.Q_ARG(str, str(e)))
            return

        local = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0"
        update_available = (local != latest)

        QtCore.QMetaObject.invokeMethod(
            self, "on_check_done", QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(bool, update_available),
            QtCore.Q_ARG(str, latest)
        )

    @QtCore.Slot(bool, str)
    def on_check_done(self, update_available, latest):
        self.btn_check.setEnabled(True)  # opcional: ocultar botones
        self.btn_update.setEnabled(True)
        
        if update_available or not self.game_installed():
            self.set_status(f"Nueva versión disponible: {latest}. Actualizando automáticamente...")
            self.on_update()  # llama directamente al update
        else:
            self.set_status("Tu panel está actualizado.")
            self.start_autostart_countdown()

    @QtCore.Slot(str)
    def on_check_failed(self, err):
        self.btn_check.setEnabled(True)
        self.set_status(f"Error: {err}")

    # ------------ UPDATE ----------

    def on_update(self):
        # Deshabilitar botones mientras se actualiza
        self.btn_check.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_delete_data.setEnabled(False)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.set_status("Descargando versión...")
        Thread(target=self._update_thread, daemon=True).start()

    def _update_thread(self):
        try:
            # Cerrar procesos existentes antes de actualizar
            self.set_status("Cerrando procesos existentes...")
            kill_running_processes()
            # Dar un momento para que los procesos y los identificadores de archivo se liberen
            time.sleep(2)

            if sys.platform.startswith("win"):
                downloads = [
                    (BUILD_URL_WIN_PART1, "Build.zip"),
                ]
            else:
                downloads = [
                    (BUILD_URL_LINUX, "BuildLinux.zip"),
                ]

            def progress_cb(downloaded, total):
                percent = int(downloaded * 100 / total) if total else 0
                QtCore.QMetaObject.invokeMethod(
                    self.progress, "setValue",
                    QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(int, percent)
                )

            for idx, (url, zip_name) in enumerate(downloads):
                zip_path = DOWNLOAD_DIR / zip_name
                self.set_status(f"Descargando {zip_name}...")
                download_file(url, zip_path, progress_cb)

                if idx == 0:
                    clean_old_version(BUILD_DIR)

                self.set_status(f"Extrayendo {zip_name}...")
                extract_zip(zip_path, BUILD_DIR)

                # eliminar archivo zip descargado
                try:
                    zip_path.unlink()
                except Exception:
                    pass

            if sys.platform.startswith("win"):
                self.set_status("Descargando start.exe...")
                start_exe_path = BUILD_DIR / "start.exe"
                download_file(START_EXE_URL, start_exe_path)

            # Siempre descargar y extraer la configuración del usuario, sobreescribiendo los archivos existentes.
            self.set_status("Descargando configuración de usuario...")
            user_zip_path = DOWNLOAD_DIR / "user.zip"
            try:
                download_file(USER_ZIP_URL, user_zip_path)
                self.set_status("Extrayendo configuración de usuario...")
                # Se extrae en la raíz de la instalación (mcsmanager) para que las rutas
                # internas del zip (ej: web/data/User/...) se coloquen correctamente.
                extract_zip(user_zip_path, BUILD_DIR)
            except Exception as e:
                print(f"Error al descargar/extraer user.zip: {e}")

            self.set_status("Descargando version.txt...")
            version = requests.get(VERSION_URL, timeout=30).text.strip()
            VERSION_FILE.write_text(version, encoding="utf-8")

            # Eliminar archivos descargados en DOWNLOAD_DIR al terminar la actualización
            try:
                for p in DOWNLOAD_DIR.iterdir():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
            except Exception:
                pass

            QtCore.QMetaObject.invokeMethod(
                self, "on_update_done",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, version)
            )

        except Exception as e:
            QtCore.QMetaObject.invokeMethod(
                self, "on_update_error",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, str(e))
            )

    @QtCore.Slot(str)
    def on_update_done(self, version):
        self.progress.setVisible(False)
        self.refresh_version_display()
        self.load_release_notes()
        self.start_autostart_countdown()

    def start_autostart_countdown(self):
        self.autostart_seconds = 15
        self.btn_cancel_autostart.setVisible(True)
        
        self.autostart_timer = QtCore.QTimer(self)
        self.autostart_timer.timeout.connect(self.on_timer_tick)
        self.autostart_timer.start(1000)
        self.on_timer_tick()

    def on_timer_tick(self):
        if self.autostart_seconds > 0:
            self.set_status(f"Iniciando en {self.autostart_seconds}s...")
            self.autostart_seconds -= 1
        else:
            self.autostart_timer.stop()
            self.btn_cancel_autostart.setVisible(False)
            self.on_start()

    def cancel_autostart(self):
        if hasattr(self, 'autostart_timer'):
            self.autostart_timer.stop()
        self.btn_cancel_autostart.setVisible(False)
        self.set_status("Actualización completada.")
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_delete_data.setEnabled(True)

    @QtCore.Slot(str)
    def on_update_error(self, err):
        self.progress.setVisible(False)
        self.set_status(f"Error: {err}")
        
        # Habilitar botones nuevamente
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_delete_data.setEnabled(True)

    # ------------ START ----------

    def on_start(self):
        # Stop autostart timer if running (e.g. manual start click)
        if hasattr(self, 'autostart_timer') and self.autostart_timer.isActive():
            self.autostart_timer.stop()
            self.btn_cancel_autostart.setVisible(False)

        # Check if the panel is already running
        if are_panel_processes_running():
            self.set_status("El panel ya se encuentra en ejecución.")
            return

        # Cerrar instancias anteriores antes de iniciar una nueva
        self.set_status("Cerrando instancias anteriores...")
        kill_running_processes()
        time.sleep(1)

        try:
            start_game_process()
            # Cerrar el launcher
            QtWidgets.QApplication.quit()
        except Exception as e:
            self.set_status(f"Error al iniciar: {e}")
            self.btn_check.setEnabled(True)
            self.btn_update.setEnabled(True)
            self.btn_start.setEnabled(True)
            self.btn_delete_data.setEnabled(True)
            
    # --------- GAME INSTALLED CHECK -----------
    
    def game_installed(self):
        return VERSION_FILE.exists() and BUILD_DIR.exists()
    
    # ------------ LOAD RELEASE NOTES ------------
    
    def load_release_notes(self):
        try:
            resp = requests.get(RELEASE_NOTES_URL, timeout=20)
            resp.raise_for_status()
            notes = resp.text.strip()
        except:
            notes = "No hay notas de la versión disponibles."

        self.release_notes_box.setText(notes)



# --------------- MAIN ---------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = LauncherWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
