# .build — Generador de PDF de la documentación

Este directorio convierte la KB (`knowledge-base/*.md`) y el PRD (`docs/PRD.md`) en un **único PDF** consolidado.

## Uso

Desde la **raíz del proyecto**:

```bash
cd .build
npm run pdf
```

Eso ejecuta:
1. `build.js` → concatena los 13 archivos `.md` en `activia-trace-doc.html` con CSS de print-friendly.
2. `pdf.js` → lanza Chrome headless y produce `../activia-trace-documentacion.pdf` (en la raíz del proyecto).

**Salida**: `activia-trace-documentacion.pdf` en la raíz del proyecto (~2 MB).

## Comandos disponibles

| Comando | Qué hace |
|---------|---------|
| `npm run html` | Solo regenera el HTML intermedio (útil para previsualizar en el browser) |
| `npm run pdf` | Regenera HTML + PDF (el flujo completo) |
| `npm run clean` | Borra el HTML y el PDF generado *(requiere `rimraf` si no está, sino borralos manual)* |

## Dependencias

- **Node.js** (en PATH).
- **Google Chrome** (busca automáticamente en ubicaciones típicas; podés forzar con la env var `CHROME_PATH=ruta/chrome.exe`).
- **`marked`** (instalado en `node_modules/`, ya bundle en el repo).

## Cuándo regenerar

Cuando edites cualquiera de estos `.md`, corré `npm run pdf` de nuevo:

- `knowledge-base/README.md`
- `knowledge-base/01..11_*.md`
- `docs/PRD.md`

Si agregás un archivo nuevo a la KB o al PRD, también editá el array `files` en `build.js` para incluirlo.

## Estructura interna

```
.build/
├── package.json           — scripts y dependencia de marked
├── build.js               — MD → HTML (con CSS embebido)
├── pdf.js                 — HTML → PDF (Chrome headless, autodetecta ejecutable)
├── README.md              — este archivo
├── node_modules/          — sólo `marked` (gitignore recomendado)
└── activia-trace-doc.html — output intermedio (gitignore recomendado)
```

## Troubleshooting

**"Chrome no encontrado"** → exportá la ruta:
```bash
# Windows (Git Bash)
CHROME_PATH="/c/Program Files/Google/Chrome/Application/chrome.exe" npm run pdf

# Windows (PowerShell)
$env:CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
npm run pdf
```

**"Falta el HTML"** al correr solo `node pdf.js` → corré `npm run html` primero, o usá `npm run pdf` que encadena ambos.

**Chrome warnings de USB / GPU** en la salida → ruido normal en Windows headless, ignoralos. Lo único que importa es la línea final `OK: PDF generado (X.XX MB) en ...`.
