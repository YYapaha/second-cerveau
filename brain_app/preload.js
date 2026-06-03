const { contextBridge, shell } = require('electron');

contextBridge.exposeInMainWorld('BRAIN_API_URL', 'http://127.0.0.1:7842');
contextBridge.exposeInMainWorld('openUrl', (url) => {
  if (/^https?:\/\//.test(url)) shell.openExternal(url);
});
