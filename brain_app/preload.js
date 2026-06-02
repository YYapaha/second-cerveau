const { contextBridge } = require('electron');

// Expose l'URL de l'API au renderer sans exposer Node.js
contextBridge.exposeInMainWorld('BRAIN_API_URL', 'http://127.0.0.1:7842');
