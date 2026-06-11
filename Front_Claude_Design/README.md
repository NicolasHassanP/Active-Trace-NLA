# Front_Claude_Design — Constancia de herramienta de diseño

> Esta carpeta deja **constancia de la herramienta usada para el diseño del frontend** de activia-trace.

## Herramienta utilizada

El rediseño visual del frontend (Design v1) se generó con **Claude Design** (Anthropic) como herramienta de diseño. **No** se usó Stitch, Figma Make, v0, ni otra herramienta de generación de UI.

- **Herramienta**: Claude Design (Anthropic)
- **Fecha del handoff**: 2026-06-06 (design handoff v1)
- **Alcance**: sistema de diseño (design tokens, tipografía, espaciado, componentes) + prototipo de alta fidelidad de todas las pantallas por rol.

## Contenido

`design_handoff/` es el paquete de entrega producido por la herramienta:

| Archivo | Contenido |
|---------|-----------|
| `design_handoff/README.md` | Spec de diseño: design tokens, tipografía, componentes y detalle pantalla por pantalla |
| `design_handoff/Activia Prototipo.html` | Prototipo interactivo de alta fidelidad (abrir en navegador) |
| `design_handoff/proto/*.jsx`, `screens/*.jsx` | Código de prototipo (referencia visual — **no** es el frontend real; el frontend se reimplementó en React + Tailwind) |
| `design_handoff/docs/analisis-*.md` | Análisis de documentación y de CHANGES.md hechos durante el diseño |

## Estado

El handoff **ya fue consumido**: el frontend real (`frontend/`) se construyó a partir de esta referencia (changes C-21/C-22/C-23 archivados). Se conserva como **referencia visual congelada** para el change pendiente **C-24** (frontend finanzas/admin) y como registro de la herramienta empleada.
