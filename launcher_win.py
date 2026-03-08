#!/usr/bin/env python3
import sys
import os
import shutil
import zipfile
import subprocess
from pathlib import Path
from threading import Thread

import requests
from PySide6 import QtCore, QtWidgets, QtGui

# ---------------- CONFIG ------------------

LAUNCHER_VERSION = "1.0.0"

# Windows build is split into two parts
BUILD_URL_WIN_PART1 = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/Build.zip"
BUILD_URL_LINUX = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/Build.zip"
VERSION_URL = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/version.txt"
RELEASE_NOTES_URL = "https://github.com/acierto-incomodo/mcsmanager-launcher/releases/latest/download/ReleaseNotes.txt"

EXE_NAME_WIN   = "start.bat"
EXE_NAME_LINUX = "start.bat"

DOWNLOAD_DIR = Path.cwd() / "downloads"
GAME_DIR     = Path.cwd() / "files"
VERSION_FILE = GAME_DIR / "version.txt"
BUILD_DIR    = GAME_DIR / "mcsmanager"

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

    if sys.platform.startswith("win"):
        os.startfile(str(exe))
    else:
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
        self.btn_start  = QtWidgets.QPushButton("Iniciar juego")

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

        tools_layout.addWidget(self.btn_open_folder)
        tools_layout.addWidget(self.btn_delete_data)

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

        self.btn_update.setEnabled(False)

    def set_status(self, text):
        self.status.setText(text)

    def refresh_version_display(self):
        if VERSION_FILE.exists():
            try:
                content = VERSION_FILE.read_text(encoding="utf-8").strip()
                self.version_display.setText(content or "Necesitas descargar el juego")
            except:
                self.version_display.setText("Necesitas descargar el juego")
        else:
            self.version_display.setText("Necesitas descargar el juego")

    # ------------ NUEVA FUNCIÓN: ABRIR UBICACIÓN ------------

    def open_location(self):
        folder = str(Path.cwd())
        if sys.platform.startswith("win"):
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    # ------------ NUEVA FUNCIÓN: ELIMINAR DATOS ------------

    def delete_data(self):
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
            self.set_status("Tu juego está actualizado.")

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
            if sys.platform.startswith("win"):
                downloads = [
                    (BUILD_URL_WIN_PART1, "Part1.zip"),
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
