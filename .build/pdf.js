// Convierte el HTML consolidado a PDF usando Chrome en modo headless.
// Detecta el ejecutable de Chrome en ubicaciones típicas de Windows/macOS/Linux.

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const HTML  = path.resolve(__dirname, 'activia-trace-doc.html');
const PDF   = path.resolve(__dirname, '..', 'activia-trace-documentacion.pdf');
const URL   = 'file:///' + HTML.replace(/\\/g, '/');

const candidates = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  process.env.LOCALAPPDATA && `${process.env.LOCALAPPDATA}/Google/Chrome/Application/chrome.exe`,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium-browser',
  '/usr/bin/chromium',
].filter(Boolean);

const chrome = candidates.find((p) => {
  try { fs.accessSync(p, fs.constants.X_OK); return true; } catch { return false; }
});

if (!chrome) {
  console.error('Chrome no encontrado. Probados:');
  candidates.forEach((c) => console.error('  -', c));
  console.error('Definí CHROME_PATH como variable de entorno para forzar la ruta.');
  process.exit(1);
}

if (!fs.existsSync(HTML)) {
  console.error('Falta el HTML:', HTML);
  console.error('Corré primero "npm run html".');
  process.exit(1);
}

console.log('Chrome:', chrome);
console.log('Input :', URL);
console.log('Output:', PDF);

try {
  execFileSync(chrome, [
    '--headless',
    '--disable-gpu',
    '--no-pdf-header-footer',
    `--print-to-pdf=${PDF}`,
    URL,
  ], { stdio: 'inherit' });
} catch (err) {
  // Chrome a veces escribe el PDF y luego sale con código no-cero por warnings.
  // Verificamos el archivo igual.
}

if (fs.existsSync(PDF)) {
  const sizeMB = (fs.statSync(PDF).size / 1024 / 1024).toFixed(2);
  console.log(`\nOK: PDF generado (${sizeMB} MB) en ${PDF}`);
} else {
  console.error('FALLO: el PDF no se generó.');
  process.exit(1);
}
