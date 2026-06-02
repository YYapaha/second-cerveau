const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

function getTargetDisplay() {
  const displays = screen.getAllDisplays();
  // Utilise l'écran 3 (index 2) si disponible, sinon le dernier écran
  return displays.length >= 3 ? displays[2] : displays[displays.length - 1];
}

function createWindow() {
  const display = getTargetDisplay();
  const { x, y, width, height } = display.bounds;

  const win = new BrowserWindow({
    x, y, width, height,
    frame: false,
    backgroundColor: '#0a0a0f',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.loadFile('index.html');
  win.maximize();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
