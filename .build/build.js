const fs = require('fs');
const path = require('path');
const { marked } = require('marked');

const ROOT = path.resolve(__dirname, '..');
const KB = path.join(ROOT, 'knowledge-base');
const DOCS = path.join(ROOT, 'docs');
const OUT_HTML = path.join(__dirname, 'activia-trace-doc.html');

const files = [
  { path: path.join(KB, 'README.md'),                       label: 'KB · Índice' },
  { path: path.join(KB, '01_vision_y_objetivos.md'),        label: 'KB · 01 — Visión y Objetivos' },
  { path: path.join(KB, '02_descripcion_general.md'),       label: 'KB · 02 — Descripción General' },
  { path: path.join(KB, '03_actores_y_roles.md'),           label: 'KB · 03 — Actores y Roles' },
  { path: path.join(KB, '04_modelo_de_datos.md'),           label: 'KB · 04 — Modelo de Datos' },
  { path: path.join(KB, '05_reglas_de_negocio.md'),         label: 'KB · 05 — Reglas de Negocio' },
  { path: path.join(KB, '06_funcionalidades.md'),           label: 'KB · 06 — Funcionalidades' },
  { path: path.join(KB, '07_flujos_principales.md'),        label: 'KB · 07 — Flujos Principales' },
  { path: path.join(KB, '08_arquitectura_propuesta.md'),    label: 'KB · 08 — Arquitectura' },
  { path: path.join(KB, '09_decisiones_y_supuestos.md'),    label: 'KB · 09 — Decisiones y Supuestos' },
  { path: path.join(KB, '10_preguntas_abiertas.md'),        label: 'KB · 10 — Preguntas Abiertas' },
  { path: path.join(KB, '11_historias_de_usuario.md'),      label: 'KB · 11 — Historias de Usuario' },
  { path: path.join(DOCS, 'PRD.md'),                        label: 'PRD — activia-trace' },
  { path: path.join(DOCS, 'ARQUITECTURA.md'),               label: 'Arquitectura — activia-trace (destino)' },
];

marked.setOptions({
  breaks: false,
  gfm: true,
});

const css = `
@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #1a1a1a;
  margin: 0;
  padding: 0;
}
.cover {
  page-break-after: always;
  text-align: center;
  padding-top: 70mm;
}
.cover h1 {
  font-size: 36pt;
  margin: 0 0 10mm 0;
  font-weight: 700;
  letter-spacing: -0.5pt;
}
.cover .subtitle {
  font-size: 14pt;
  color: #555;
  margin-bottom: 30mm;
}
.cover .meta {
  font-size: 10pt;
  color: #888;
  border-top: 1px solid #ddd;
  padding-top: 8mm;
  width: 60%;
  margin: 0 auto;
}
.toc {
  page-break-after: always;
}
.toc h2 {
  font-size: 22pt;
  border-bottom: 2px solid #1a1a1a;
  padding-bottom: 3mm;
  margin-top: 0;
}
.toc ol { padding-left: 0; list-style-position: inside; }
.toc li { padding: 2mm 0; font-size: 11pt; }
.toc .label { font-weight: 600; }
.section {
  page-break-before: always;
}
.section-header {
  border-bottom: 2px solid #1a1a1a;
  margin-bottom: 6mm;
  padding-bottom: 2mm;
}
.section-header .tag {
  display: inline-block;
  background: #1a1a1a;
  color: #fff;
  padding: 1mm 3mm;
  font-size: 8pt;
  font-weight: 600;
  letter-spacing: 0.5pt;
  text-transform: uppercase;
  margin-bottom: 2mm;
}
h1 { font-size: 22pt; margin: 6mm 0 4mm 0; font-weight: 700; }
h2 { font-size: 16pt; margin: 7mm 0 3mm 0; font-weight: 700; border-bottom: 1px solid #ddd; padding-bottom: 1mm; }
h3 { font-size: 13pt; margin: 6mm 0 2mm 0; font-weight: 600; }
h4 { font-size: 11.5pt; margin: 5mm 0 2mm 0; font-weight: 600; color: #333; }
h5 { font-size: 10.5pt; margin: 4mm 0 1.5mm 0; font-weight: 600; color: #444; }
p { margin: 0 0 3mm 0; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 3mm 0; padding-left: 6mm; }
li { margin: 0.6mm 0; }
strong { color: #000; }
em { color: #444; }
hr { border: none; border-top: 1px solid #ddd; margin: 5mm 0; }
blockquote {
  border-left: 3px solid #888;
  padding: 1mm 3mm;
  margin: 3mm 0;
  background: #f6f6f6;
  color: #444;
  font-size: 10pt;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
}
th, td {
  border: 1px solid #ccc;
  padding: 1.5mm 2.5mm;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f0f0f0;
  font-weight: 600;
}
tr:nth-child(even) td { background: #fafafa; }
code {
  font-family: "Consolas", "Monaco", "Menlo", monospace;
  background: #f4f4f4;
  padding: 0.3mm 1mm;
  border-radius: 1.5px;
  font-size: 9.5pt;
  color: #c7254e;
}
pre {
  background: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 3px;
  padding: 3mm 4mm;
  font-size: 8.5pt;
  line-height: 1.4;
  overflow-x: auto;
  page-break-inside: avoid;
  margin: 3mm 0;
}
pre code {
  background: transparent;
  padding: 0;
  color: #24292e;
  font-size: 8.5pt;
}
a { color: #1a1a1a; text-decoration: underline; }
.markdown img { max-width: 100%; }
`;

function slugify(label) {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

const today = new Date().toISOString().slice(0, 10);

let body = `
<div class="cover">
  <div style="font-size: 10pt; color: #888; letter-spacing: 4pt; margin-bottom: 8mm;">DOCUMENTACIÓN INTEGRAL</div>
  <h1>activia-trace</h1>
  <div class="subtitle">Base de Conocimiento + Product Requirements Document + Arquitectura</div>
  <div class="meta">
    Generado el ${today}<br/>
    Plataforma de gestión académica y trazabilidad de actividades estudiantiles<br/>
    ${files.length} secciones · 1 PDF consolidado
  </div>
</div>
<div class="toc">
  <h2>Índice del documento</h2>
  <ol>
`;

for (const f of files) {
  const slug = slugify(f.label);
  body += `<li><span class="label">${f.label}</span></li>\n`;
}

body += `</ol></div>\n`;

for (const f of files) {
  if (!fs.existsSync(f.path)) {
    console.warn('FALTA:', f.path);
    continue;
  }
  const raw = fs.readFileSync(f.path, 'utf8');
  const html = marked.parse(raw);
  const slug = slugify(f.label);
  const isKB = f.label.startsWith('KB');
  const isArch = f.label.startsWith('Arquitectura');
  const tag = isKB ? 'Knowledge Base' : isArch ? 'Arquitectura (destino)' : 'Product Requirements Document';
  body += `
<div class="section" id="${slug}">
  <div class="section-header">
    <div class="tag">${tag}</div>
  </div>
  <div class="markdown">
    ${html}
  </div>
</div>
`;
}

const fullHtml = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>activia-trace · Documentación Integral</title>
<style>${css}</style>
</head>
<body>
${body}
</body>
</html>`;

fs.writeFileSync(OUT_HTML, fullHtml);
console.log('HTML generated:', OUT_HTML);
console.log('Size:', (fs.statSync(OUT_HTML).size / 1024).toFixed(1), 'KB');
