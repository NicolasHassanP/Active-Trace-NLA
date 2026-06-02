---
name: kb-creator
description: >
  Builds a structured project knowledge base of 10 canonical .md files at knowledge-base/ (project root). Has dual mode: silent generation from existing source documents in docs/, or interactive iterative creation from scratch.
  Trigger: When user asks to create, build, or generate a knowledge base for a project, document a project from source documents (.txt, .docx, .pdf), or asks to "armar base de conocimiento" / "crear KB" / "documentar proyecto".
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Generar una base de conocimiento estructurada y navegable para un proyecto.
- Convertir documentos monolíticos (`.txt`, `.docx`, `.pdf`, `.md` largos) en una KB temática.
- Documentar un sistema desde cero acompañando al usuario como socio estratégico.

**Don't use when:**
- Ya existe `knowledge-base/` con los 10 archivos canónicos completos (sugerí actualizar archivos puntuales en su lugar).
- El usuario pide UN documento específico (es una skill de KB completa, no de archivos sueltos).

---

## Operating Modes

Esta skill **auto-detecta el modo** al iniciar:

### Mode A — From existing source docs (silent)

**Trigger automático**: la carpeta `docs/` existe **y** contiene archivos fuente (`.txt`, `.docx`, `.pdf`, o `.md` distintos a un README).

**Comportamiento**: leés todas las fuentes desde `docs/`, analizás, y generás la KB canónica completa en `knowledge-base/` (raíz del proyecto) **sin hacer preguntas**. Fire-and-forget.

### Mode B — From scratch (interactive)

**Trigger automático**: la carpeta `docs/` no existe, está vacía, o solo tiene un README, **y** `knowledge-base/` no existe en raíz.
**Trigger explícito**: el usuario dice "armemos desde cero", "construyamos la KB", "no tengo documentación previa".

**Comportamiento**: actuás como **socio estratégico** — analizás contexto, detectás huecos, hacés 3-5 preguntas estratégicas, proponés enfoques con pros/contras, iterás archivo por archivo con validación.

---

## Critical Patterns

### Output location (ambos modos)
Todos los archivos de la KB van a `knowledge-base/` en la **raíz del proyecto**. **NUNCA** mezclar con `docs/` (que contiene los documentos fuente).

### Canonical files (10 obligatorios)

La KB **DEBE** contener estos 10 archivos con estos nombres exactos:

| # | Archivo | Contenido |
|---|---------|-----------|
| 01 | `01_vision_y_objetivos.md` | Propósito, objetivos por actor, alcance, fuera de alcance |
| 02 | `02_descripcion_general.md` | Stack tecnológico, arquitectura general, integraciones externas |
| 03 | `03_actores_y_roles.md` | Actores del sistema, tabla RBAC, permisos, rutas públicas |
| 04 | `04_modelo_de_datos.md` | Entidades, ERD, relaciones, seed data |
| 05 | `05_reglas_de_negocio.md` | Reglas codificadas por dominio (con códigos tipo RN-XX) |
| 06 | `06_funcionalidades.md` | Historias de usuario / features organizadas por épica |
| 07 | `07_flujos_principales.md` | Flujos extremo a extremo (auth, dominio principal, etc.) |
| 08 | `08_arquitectura_propuesta.md` | Patrones, estructura de directorios, seguridad, env vars |
| 09 | `09_decisiones_y_supuestos.md` | Decisiones de diseño documentadas + supuestos inferidos |
| 10 | `10_preguntas_abiertas.md` | Inconsistencias detectadas + preguntas abiertas priorizadas |

Más un `README.md` índice en `knowledge-base/README.md`.

Ver `assets/canonical-templates.md` para la estructura interna esperada de cada archivo.

### Optional extras (permitidos)

Si el dominio lo requiere, podés agregar archivos extra con prefijo `1X_` o `2X_` y nombre kebab-case. Ejemplos:
- `11_pagos_mercadopago.md` (e-commerce con pasarela específica)
- `12_devops_y_despliegue.md` (proyecto con infra compleja)
- `13_observabilidad.md` (sistema con telemetría no trivial)

Los extras **nunca reemplazan** los 10 canónicos — los complementan.

### Mode A workflow (silent)

1. `glob docs/*.{txt,docx,pdf,md}` — enumerá las fuentes (excluí README).
2. Leé todas las fuentes.
3. Para cada archivo canónico, extraé contenido relevante de las fuentes y estructuralo siguiendo `assets/canonical-templates.md`.
4. Si una fuente cubre dominios extra (ej. pagos con un PSP específico), creá un archivo extra `1X_*.md`.
5. Escribí los 10 canónicos + extras + `README.md`.
6. Cerrá con una tabla resumen: `archivo → líneas → temas cubiertos`.

**No hagas preguntas en este modo.** Si una fuente es ambigua, registrá la duda en `10_preguntas_abiertas.md` y seguí.

### Mode B workflow (interactive)

1. Analizá contexto disponible (nombre del repo, mensaje del usuario, archivos visibles).
2. Resumí en un párrafo qué entendés del proyecto.
3. Listá las **incertidumbres principales** (3-5).
4. Proponé 2-3 enfoques iniciales con pros y contras.
5. Hacé las **3-5 preguntas estratégicas** (ver `assets/strategic-questions.md`).
6. Esperá respuesta del usuario antes de generar archivos.
7. Después, proponé estructura inicial de la KB y validá.
8. Iterá archivo por archivo, escribiendo + pidiendo feedback.

### Tono según modo
- **Mode A**: eficiente, factual, sin floreos.
- **Mode B**: arquitecto senior + product manager. Cuestiona decisiones débiles. Marcá supuestos con `**Suposición:**`. Proponé alternativas. Detectá riesgos.

---

## Code Examples

### Mode A: tabla resumen al cerrar

```markdown
## KB generada en knowledge-base/

| Archivo | Líneas | Temas cubiertos |
|---------|--------|-----------------|
| 01_vision_y_objetivos.md | 84 | Propósito, 3 actores, alcance v5.0 |
| 02_descripcion_general.md | 132 | FastAPI + React, REST, 14 endpoints |
| ...
```

### Mode B: pregunta estratégica modelo

```markdown
**Pregunta 2 de 4 — Alcance del MVP**

¿Cuál es el alcance MÍNIMO viable para considerar el sistema "lanzable"?

- (a) Solo flujo de compra (catálogo + carrito + checkout simulado).
- (b) Flujo completo con pago real integrado.
- (c) Pago + panel admin con métricas.

**Por qué importa**: define qué entra en la primera versión y qué se posterga. Una respuesta vaga acá te genera scope creep en sprint 2.
```

---

## Commands

```bash
# Instalar la skill
npx skills add https://github.com/JuanCruzRobledo/kb-creator

# Invocar en el agente (carga automática por contexto):
"crear base de conocimiento del proyecto"
"generar KB desde los docs"
"armemos la documentación desde cero"
```

---

## Resources

- **Templates**: ver [assets/canonical-templates.md](assets/canonical-templates.md) — estructura interna esperada de los 10 archivos canónicos.
- **Strategic questions**: ver [assets/strategic-questions.md](assets/strategic-questions.md) — banco de preguntas para Mode B.
