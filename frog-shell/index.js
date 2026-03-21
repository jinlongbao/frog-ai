// Frog AI Core - Ultimate Robust Launcher
let electron;
try {
    electron = require('electron');
    if (typeof electron === 'string') {
        process.stdout.write('Detecting shadowed "electron" module. Attempting bypass...\n');
        // Delete the string from the cache
        delete require.cache[require.resolve('electron')];
        // This is a common Electron/Node resolution conflict.
        // In the Electron runtime, 'electron' should be internal.
        // If we got here, Node's loader is winning.
        electron = undefined;
    }
} catch (e) {}

if (!electron || typeof electron === 'string') {
    try {
        // Some versions of Electron allow this
        electron = require('electron/index.js'); 
    } catch (e) {}
}

if (!electron || typeof electron === 'string') {
    // Last ditch: if we're in Electron, we should have access to the API even if require fails.
    // However, some versions are strict.
    process.stderr.write('CRITICAL: Could not load Electron API. Please check your environment.\n');
}

const { app, BrowserWindow, ipcMain } = electron || {};

if (!app) {
    process.stderr.write('CRITICAL: "app" is undefined. Startup failed.\n');
    process.exit(1);
}

const path = require('path');
const { spawn } = require('child_process');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    titleBarStyle: 'hidden',
    frame: false
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(() => {
  console.log('Frog Shell: Ready and running.');
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
