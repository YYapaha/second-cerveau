const { app, BrowserWindow, screen, ipcMain, shell } = require('electron');
const path = require('path');

function getTargetDisplay() {
  const displays = screen.getAllDisplays();
  const portrait = displays.find(d => d.bounds.height > d.bounds.width);
  return portrait || displays[displays.length - 1];
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

app.whenReady().then(() => {
  createWindow();
  ipcMain.on('open-url', (_, url) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
