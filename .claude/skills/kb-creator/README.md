# kb-creator

Skill para construir **bases de conocimiento estructuradas** (10 archivos canónicos `.md`) sobre cualquier proyecto, automáticamente o de forma iterativa.

---

## ¿Qué hace?

Genera una base de conocimiento navegable y consistente en `knowledge-base/` (raíz del proyecto) siguiendo un contrato de **10 archivos canónicos** que cubren todos los aspectos críticos de un sistema:

1. Visión y objetivos
2. Descripción general
3. Actores y roles
4. Modelo de datos
5. Reglas de negocio
6. Funcionalidades
7. Flujos principales
8. Arquitectura propuesta
9. Decisiones y supuestos
10. Preguntas abiertas

Tiene **dos modos** que se activan automáticamente:

- **Mode A — silent**: si tu carpeta `docs/` ya tiene documentos fuente (`.txt`, `.docx`, `.pdf`, `.md`), genera la KB completa sin hacer preguntas.
- **Mode B — interactive**: si no hay documentación previa, actúa como **arquitecto senior + product manager**, haciéndote 3-5 preguntas estratégicas por ronda hasta construir la KB de forma colaborativa.

---

## Instalación

```bash
npx skills add https://github.com/JuanCruzRobledo/kb-creator
```

La skill queda disponible para tu agente. Se carga automáticamente cuando le pidas crear, generar o armar una base de conocimiento.

---

## Uso

### Mode A (silent) — proyecto con documentos fuente

```
Tu repo:
proyecto/
├── docs/
│   ├── descripcion.txt
│   ├── historias_de_usuario.docx
│   └── arquitectura.pdf

Le decís al agente:
"creá la base de conocimiento del proyecto"
```

→ El agente lee los 3 documentos de `docs/` y genera `knowledge-base/` en la raíz con los 10 archivos + `README.md` índice.

### Mode B (interactive) — proyecto desde cero

```
Tu repo:
proyecto/
└── (sin docs/ o vacío)

Le decís al agente:
"armemos la base de conocimiento desde cero"
```

→ El agente empieza haciendo 3-5 preguntas estratégicas (visión, alcance, actores, restricciones técnicas, prioridades), iteran, y va construyendo la KB archivo por archivo con tu validación.

---

## Estructura de la KB generada

```
proyecto/
├── docs/                              # Documentos fuente (entrada)
│   ├── descripcion.txt
│   └── ...
└── knowledge-base/                    # KB generada (salida) — RAÍZ del proyecto
    ├── README.md                      # Índice + resumen ejecutivo
    ├── 01_vision_y_objetivos.md
    ├── 02_descripcion_general.md
    ├── 03_actores_y_roles.md
    ├── 04_modelo_de_datos.md
    ├── 05_reglas_de_negocio.md
    ├── 06_funcionalidades.md
    ├── 07_flujos_principales.md
    ├── 08_arquitectura_propuesta.md
    ├── 09_decisiones_y_supuestos.md
    ├── 10_preguntas_abiertas.md
    └── 11_xxx.md, 12_xxx.md, ...      # Extras opcionales según dominio
```

Los 10 canónicos son **siempre obligatorios**. Si el dominio lo requiere (ej. e-commerce con pasarela de pago específica), la skill agrega archivos extra con prefijo `1X_` y nombre kebab-case.

---

## Por qué esta estructura

- **Consistencia**: cualquier proyecto documentado con esta skill comparte la misma estructura → onboarding más rápido.
- **Compatibilidad con OpenSpec**: la KB es input directo para `/opsx:explore` y skills de roadmap (como `roadmap-generator`).
- **Trazabilidad de decisiones**: el archivo 09 fuerza a documentar el porqué de cada elección → menos discusiones futuras "¿por qué hicimos esto así?".
- **Visibilidad de huecos**: el archivo 10 hace explícitas las preguntas pendientes → no quedan tapadas en commits o threads de Slack.

---

## Licencia

Apache-2.0
