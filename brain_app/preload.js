const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('BRAIN_API_URL', 'http://127.0.0.1:7842');
contextBridge.exposeInMainWorld('openUrl', (url) => {
  ipcRenderer.send('open-url', url);
});
