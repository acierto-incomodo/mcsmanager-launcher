const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const { autoUpdater } = require('electron-updater');

const PANEL_URL = 'http://localhost:23333';
let mainWindow;

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, '../mcsmanager-launcher.ico')
  });

  mainWindow.loadURL(PANEL_URL);

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    if (errorDescription !== 'ABORTED') { // Ignorar errores de aborto
      mainWindow.loadFile('error.html');
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

const menuTemplate = [
  {
    label: 'Navegación',
    submenu: [
      {
        label: 'Recargar Panel',
        accelerator: 'CmdOrCtrl+R',
        click: () => {
          if (mainWindow) {
            mainWindow.loadURL(PANEL_URL);
          }
        },
      },
      {
        label: 'Forzar Recarga (sin caché)',
        accelerator: 'CmdOrCtrl+Shift+R',
        click: () => {
          if (mainWindow) {
            mainWindow.webContents.reloadIgnoringCache();
          }
        },
      },
      { type: 'separator' },
      { role: 'quit', label: 'Salir' }
    ],
  },
  {
    label: 'Herramientas',
    submenu: [
      {
        label: 'Abrir Inspector',
        accelerator: 'CmdOrCtrl+Shift+I',
        click: () => {
          if (mainWindow && mainWindow.webContents.isFocused()) {
            mainWindow.webContents.toggleDevTools();
          }
        },
      },
      {
        label: 'Buscar Actualizaciones',
        click: () => {
          if (mainWindow) {
            mainWindow.loadFile('updates.html');
          }
        },
      },
    ],
  },
];

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.on('ready', () => {
    createMainWindow();
    const menu = Menu.buildFromTemplate(menuTemplate);
    Menu.setApplicationMenu(menu);
    
    // Comprobar actualizaciones en segundo plano al iniciar
    autoUpdater.checkForUpdatesAndNotify();
  });
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createMainWindow();
  }
});

// --- Lógica de Actualización ---
ipcMain.on('check-for-update', () => {
  autoUpdater.checkForUpdates();
});

autoUpdater.on('update-available', (info) => {
  if (mainWindow) {
    mainWindow.webContents.send('update-message', `¡Actualización disponible! Versión ${info.version}. Descargando...`);
  }
});

autoUpdater.on('update-not-available', () => {
  if (mainWindow) {
    mainWindow.webContents.send('update-message', 'Estás en la última versión.');
  }
});

autoUpdater.on('update-downloaded', () => {
  if (mainWindow) {
    mainWindow.webContents.send('update-message', 'Actualización descargada. Se instalará al reiniciar.');
  }
  autoUpdater.quitAndInstall();
});

autoUpdater.on('error', (err) => {
  if (mainWindow) {
    mainWindow.webContents.send('update-message', `Error en la actualización: ${err.toString()}`);
  }
});