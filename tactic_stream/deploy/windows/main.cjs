const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn, execFile } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const { pathToFileURL } = require('node:url');

app.setName('TACTIC Stream');
const bundle = path.dirname(process.execPath);
const dataArgument = process.argv.indexOf('--data-dir');
const selectedData = app.commandLine.getSwitchValue('data-dir') || (dataArgument >= 0 ? process.argv[dataArgument + 1] : '');
if (dataArgument >= 0 && (!selectedData || selectedData.startsWith('--'))) throw new Error('--data-dir requires a directory');
const root = path.resolve(selectedData || path.join(app.getPath('appData'), 'TACTIC Stream'));
const data = path.join(root, 'server');
fs.mkdirSync(path.join(root, 'browser'), { recursive: true });
app.setPath('userData', path.join(root, 'browser'));
const python = path.join(bundle, 'runtime', 'python.exe');
const environment = { ...process.env, TACTIC_DATA_DIR: data };
for (const key of ['TACTIC_CONFIG_PATH', 'TACTIC_TMP_CONFIG_PATH', 'TACTIC_PORTS', 'PYTHONHOME', 'PYTHONPATH']) delete environment[key];
let window, backend, setup, stopping = false, finished = false;
let translate = source => source;
const t = source => translate(source, app.getLocale().startsWith('ru') ? 'ru' : 'en');

function command(arguments_) {
  return new Promise((resolve, reject) => {
    execFile(python, ['-I', '-B', '-X', 'utf8', ...arguments_], { env: environment, windowsHide: true }, (error, stdout, stderr) => {
      if (error) reject(new Error(stderr || error.message));
      else resolve(stdout);
    });
  });
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

async function finish() {
  if (stopping) return;
  stopping = true;
  if (setup && setup.exitCode === null) await new Promise(resolve => execFile('taskkill', ['/PID', String(setup.pid), '/T', '/F'], { windowsHide: true }, resolve));
  if (backend && backend.exitCode === null) {
    await command(['-m', 'tactic_stream', '--data-dir', data, 'stop']).catch(error => console.error(error));
    if (backend.exitCode === null) await new Promise(resolve => {
      const timer = setTimeout(resolve, 25000);
      backend.once('exit', () => { clearTimeout(timer); resolve(); });
    });
    if (backend.exitCode === null) await new Promise(resolve => execFile('taskkill', ['/PID', String(backend.pid), '/T', '/F'], { windowsHide: true }, resolve));
  }
  finished = true;
  app.quit();
}

async function start() {
  ({ translate } = await import(pathToFileURL(path.join(__dirname, 'strings.mjs')).href));
  const info = JSON.parse(await command([path.join(__dirname, 'desktop.py'), data, String(await freePort())]));
  if (!info.initialized) {
    await new Promise((resolve, reject) => {
      setup = spawn(python, ['-I', '-B', '-X', 'utf8', path.join(__dirname, 'desktop.py'), '--initialize', data], { env: environment, stdio: 'ignore', windowsHide: true });
      setup.once('error', reject);
      setup.once('exit', code => code === 0 ? resolve() : reject(new Error(t('Administrator initialization was cancelled or failed.'))));
    });
  }
  if (stopping) return;
  await command(['-m', 'tactic_stream', '--data-dir', data, 'upgrade']);
  fs.mkdirSync(path.join(data, 'temp', 'log'), { recursive: true });
  const log = fs.openSync(path.join(data, 'temp', 'log', 'desktop.log'), 'a');
  backend = spawn(python, ['-I', '-B', '-X', 'utf8', '-m', 'tactic_stream', '--data-dir', data, 'serve', '--host', '127.0.0.1'], { env: environment, windowsHide: true, stdio: ['ignore', log, log] });
  fs.closeSync(log);
  backend.once('error', error => { if (!stopping) { dialog.showErrorBox('TACTIC Stream', error.message); finish(); } });
  backend.once('exit', () => { if (!stopping) { dialog.showErrorBox('TACTIC Stream', t('Local server stopped. See server/temp/log/desktop.log in the data directory.')); finish(); } });
  const origin = 'http://127.0.0.1:' + info.port;
  const deadline = Date.now() + 90000;
  while (!stopping) {
    try {
      const response = await fetch(origin + '/health', { signal: AbortSignal.timeout(1500) });
      const health = await response.json();
      const status = JSON.parse(fs.readFileSync(path.join(info.log_dir, 'monitor.json'), 'utf8'));
      if (status.monitor_pid === backend.pid && status.state === 'running' && health.service === 'tactic_stream' && health.version === app.getVersion()) break;
    } catch {}
    if (Date.now() > deadline) throw new Error(t('Local server did not start. See server/temp/log/desktop.log.'));
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (stopping) return;
  window = new BrowserWindow({ width: 1280, height: 900, title: 'TACTIC Stream', show: false, webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false } });
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(origin + '/')) { event.preventDefault(); if (/^https?:/.test(url)) shell.openExternal(url); }
  });
  window.webContents.session.setPermissionRequestHandler((contents, permission, callback) => {
    if (!contents.getURL().startsWith(origin + '/')) return callback(false);
    dialog.showMessageBox(window, { type: 'question', message: t('Allow this permission?'), detail: permission, buttons: [t('Cancel'), t('Allow')], defaultId: 0, cancelId: 0 }).then(result => callback(result.response === 1));
  });
  window.webContents.on('will-prevent-unload', event => {
    if (dialog.showMessageBoxSync(window, { type: 'question', message: t('Close with unsaved changes?'), buttons: [t('Keep open'), t('Close')], defaultId: 0, cancelId: 0 }) === 1) event.preventDefault();
  });
  window.on('closed', finish);
  await window.loadURL(origin + '/');
  window.show();
}

if (!app.requestSingleInstanceLock()) { finished = true; app.quit(); }
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus(); } });
  app.on('before-quit', event => { if (!finished) { event.preventDefault(); if (window && !window.isDestroyed()) window.close(); else finish(); } });
  app.whenReady().then(start).catch(error => { if (!stopping) dialog.showErrorBox('TACTIC Stream', error.message); finish(); });
}
