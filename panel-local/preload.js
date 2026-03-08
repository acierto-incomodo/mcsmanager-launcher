const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('updater', {
  // Renderer to main
  checkForUpdate: () => ipcRenderer.send('check-for-update'),

  // Main to renderer
  onUpdateMessage: (callback) => ipcRenderer.on('update-message', (_event, ...args) => 
    callback(...args)
  ),
});