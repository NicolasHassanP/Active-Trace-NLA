# Handoff: activia-trace · Diseño completo del frontend

> Este paquete es para **Claude Code** o cualquier desarrollador que implemente el frontend real en TypeScript.  
> Los archivos HTML adjuntos son **referencias de diseño interactivas** — prototipos de alta fidelidad que muestran look, feel y comportamiento. **No copiar directamente**: recrear en el stack real del repo (`React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Hook Form + Zod`).

---

## Contexto del proyecto

**activia-trace** es una plataforma SaaS multi-tenant de gestión académica y trazabilidad. Opera como capa sobre Moodle: consolida calificaciones, detecta atrasos, gestiona comunicación saliente con aprobación, equipos docentes, encuentros, coloquios, liquidaciones y auditoría.

**Repo**: `https://github.com/NicolasHassanP/Active-Trace-NLA`  
**Stack frontend real**: React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query + React Hook Form + Zod + Axios  
**Backend**: FastAPI (Python 3.13) + PostgreSQL + JWT (access+refresh rotation) + RBAC `modulo:accion`

### Estado del roadmap al momento del handoff

| Change | Nombre | Estado |
|--------|--------|--------|
| C-21 | frontend-shell-y-auth | ✅ archivado |
| C-22 | frontend-academico-docente | ✅ archivado |
| C-23 | frontend-coordinacion | ✅ archivado |
| **C-24** | **frontend-finanzas-y-admin** | ❌ **pendiente — este handoff** |
| C-18 | liquidaciones-y-honorarios (backend) | ❌ pendiente |

**Este handoff cubre principalmente C-24** (Finanzas + Admin) más **6 correcciones** a C-22/C-23.

---

## Fidelidad

**Alta fidelidad (hifi).** El prototipo tiene colores, tipografía, espaciado e interacciones finales. Recrear pixel-perfect usando el sistema de diseño existente del repo (Tailwind) — no las clases CSS custom del prototipo.

---

## Sistema de diseño — Design Tokens

### Colores

```
--ink:   #1d2330   Texto principal
--mut:   #6b7280   Texto secundario
--faint: #9aa1ad   Texto terciario / placeholders
--line:  #eceef2   Bordes sutiles
--line2: #f3f4f7   Separadores de tabla
--bg:    #f7f8fb   Fondo de página

Acento primario (índigo):
--ind:   #4f46e5   (hover, iconos activos)
--ind2:  #4338ca   (backgrounds de botones primarios, nav activo)
Fondo acento: #eef0ff  Texto acento: --ind2

Semánticos:
--ok:    #16a34a / bg #ecfdf3    Verde éxito
--warn:  #e7515a / bg #fff1f0    Rojo error/alerta
--amber: #d97706 / bg #fef6e7    Amarillo advertencia
--vio:   #6d28d9 / bg #f3eefe    Violeta énfasis
--cyan:  #0e7490 / bg #ecfeff    Cyan/Virtual
```

### Tipografía

```
Familia: 'Manrope', system-ui, sans-serif
Pesos usados: 400 (texto), 600 (label), 700 (label fuerte), 800 (headings)

Escala:
- h1 de página:  22–23px, weight 800, letter-spacing -0.6px
- h2 sección:    16–18px, weight 800, letter-spacing -0.3px
- h3 card:       13.5–14.5px, weight 800
- body:          13–13.5px, weight 400–600
- label:         11–11.5px, weight 700
- microcopy:     10.5–11px, weight 600–700, letter-spacing 0.4–0.7px
- badge:         11px, weight 700
- monospace (IDs, fechas): ui-monospace
```

### Espaciado

```
Padding de página:     24px top, 28px horizontal (aBody)
Gap entre cards:       14–16px
Padding interno card:  18–20px
Gap de tabla (rows):   11px vertical
Border radius:
  - Página/modal:      16–18px
  - Card:              16px
  - Botón:             10px (sm: 9px)
  - Badge/pill:        999px
  - Tag/chip:          7–9px
  - Avatar:            50% (círculo)
  - Avatar cuadrado:   8–12px
```

### Sombras

```
Card en reposo:  0 1px 2px rgba(16,24,40,.04)
Card hover:      0 8px 26px rgba(16,24,40,.09)
Modal:           0 30px 80px rgba(16,24,40,.32)
Toast:           0 12px 34px rgba(0,0,0,.28)
Logo/botón pri:  0 3px 8px rgba(67,56,202,.35)
```

---

## Estructura de la aplicación

### Shell / Layout

```
┌─────────────────────────────────────────────────────┐
│  Sidebar (252px fijo)  │  Main area (flex: 1)        │
│  ├ Logo + brand        │  ├ Topbar (60px fijo)        │
│  ├ Role switcher       │  │   ├ Pill cuatrimestre      │
│  ├ Nav por rol (scroll)│  │   ├ Buscador global        │
│  └ User info + logout  │  │   ├ Bell (notif)           │
│                        │  │   └ Inbox icon             │
│                        │  └ Body (overflow-y: auto)    │
│                        │      → contenido de la vista  │
└─────────────────────────────────────────────────────┘
```

**Sidebar**: fondo `#fff`, border-right `#eceef2`.  
**Topbar**: `background: rgba(255,255,255,.85)`, `backdrop-filter: blur(6px)`, border-bottom.  
**Body**: padding `24px 28px 40px`, scroll independiente.

### Role Switcher (componente propio)

Botón en el sidebar que abre un dropdown con los 5 roles disponibles. Al cambiar:
- Se actualiza el nav (grupos y ítems según `NAV[role]`)
- Se navega al `home` del rol
- El avatar del usuario cambia de color de degradado

```
Roles y degradados:
COORDINADOR → linear-gradient(150deg, #818cf8, #4338ca)  home: 'materias'
PROFESOR    → linear-gradient(150deg, #34d399, #0a9488)  home: 'materias'
ALUMNO      → linear-gradient(150deg, #fbbf24, #d97706)  home: 'estado'
ADMIN       → linear-gradient(150deg, #f472b6, #be185d)  home: 'estructura'
FINANZAS    → linear-gradient(150deg, #34d399, #047857)  home: 'liquid'
```

### Navegación por rol

```
COORDINADOR:
  Académico:    Mis materias, Calificaciones, Padrón, Atrasados, Seguimiento, Monitor
  Gestión:      Equipos docentes, Setup cuatrimestre, Tareas
  Instancias:   Encuentros, Coloquios
  Comunicación: Avisos, Comunicaciones, Aprobaciones, Mensajes
  Sistema:      Auditoría

PROFESOR:
  Mi cátedra:   Mis materias, Calificaciones, Atrasados, Sin corregir, Seguimiento
  Instancias:   Encuentros, Coloquios, Guardias
  Trabajo:      Tareas, Comunicaciones, Mensajes

ALUMNO:
  Mi cursada:   Mi estado, Mis materias, Coloquios, Avisos, Mensajes

ADMIN:
  Estructura:   Estructura académica, Fechas de evaluación, Programas
  Personas:     Usuarios
  Operación:    Monitor, Avisos, Tareas
  Sistema:      Auditoría, Configuración, Mensajes

FINANZAS:
  Liquidaciones: Liquidaciones, Historial
  Configuración: Grilla salarial, Facturas
  Sistema:       Auditoría, Mensajes
```

---

## Primitivos / Componentes base

Todos los componentes del prototipo están en `screens/shell-a.jsx`. Recrear en Tailwind:

### `<Btn>` — Botón
```
Variantes: default (borde + fondo blanco) / pri (índigo sólido) / sm (padding reducido)
Pri:     bg #4338ca, color #fff, hover bg #3730a3
Default: bg #fff, border #eceef2, hover bg #f6f7fb
sm:      padding 7px 11px, font-size 12.5px, border-radius 9px
```

### `<Badge>` — Etiqueta de estado/rol
```
padding: 4px 9px, border-radius: 999px, font-size: 11px, font-weight: 700
Colores pasados como props (color, bg). Ver estados en estChip():
  Vigente/Activo/Activa/Hecha/Pagado/Publicado/Aprobado → #16a34a / #ecfdf3
  Pendiente/Por vencer → #d97706 / #fef6e7
  Atrasado/En riesgo/Suspendido/Cancelada → #e7515a / #fff1f0
  En curso/Abierta → #4338ca / #eef0ff
  Borrador/Cerrada/Inactivo → #6b7280 / #f1f2f5
```

### `<Combo>` — Selector con nombre real + ID de referencia
```
Estructura: [avatar 30px] [nombre + ID en monospace] [chevron]
Border: 1.5px solid #e3e6ee, border-radius: 11px
Estado activo/focused: border #4f46e5, box-shadow 0 0 0 3px rgba(79,70,229,.1)
Siempre acompañado de un toggle "¿Preferís pegar IDs?" que muestra un input de texto plano
```

### `<Modal>` — Overlay
```
Overlay: rgba(24,28,38,.42) + backdrop-filter blur(3px)
Panel: bg #fff, border-radius 18px, max-width 560px (configurable), max-height 88vh
Header: título + subtítulo + botón X (32px, border-radius 9px)
Footer: flex row, justify-content flex-end, padding 16px 22px, bg #fafbfc, border-top
Animación entrada: opacity 0→1, scale 0.96→1, translateY 8px→0, duration 220ms, ease cubic-bezier(.2,.8,.3,1)
```

### `<Toast>` — Notificación fugaz
```
Posición: fixed, bottom 26px, centrado horizontalmente
bg: #1d2330, color: #fff, border-radius: 12px
Duración: 2800ms, luego desaparece
Animación entrada: translateY 12px → 0, opacity 0→1, 250ms
```

### Tabla estándar (`aTbl`)
```
th: font-size 11px, weight 700, letter-spacing 0.4px, uppercase, color #9aa1ad
    padding 11px 14px, border-bottom #eceef2
td: padding 11px 14px, border-bottom #f3f4f7 (no aplica en última fila)
tr hover: background #fafbff
Columnas numéricas: font-variant-numeric tabular-nums, weight 700
```

### Barra de progreso
```
Contenedor: height 6px, border-radius 99px, bg #eef0f3
Relleno: gradient linear(90deg, #6366f1, #4338ca)
Variantes de color: verde (#34d399→#16a34a) para "al día", amber (#d97706) para atraso, rojo (#e7515a) para riesgo
```

### Avatar
```
Círculo: width/height 34-36px, border-radius 50%
Degradado según rol (ver Role Switcher arriba)
Texto: iniciales 2 chars, weight 700, font-size 12-13px, color #fff
```

---

## Pantallas — detalle por vista

### LOGIN
**Archivo de referencia**: `proto/app.jsx` → componente `Login`

Layout: centrado en viewport, fondo con radial-gradient índigo sutil.  
Card: max-width 420px, padding 32px 30px, border-radius 20px, box-shadow heavy.

Elementos:
1. **Brand**: logo 34px (degradado índigo, border-radius 10px) + "activia·trace" (18px, weight 800)
2. **Heading**: "Iniciá sesión" (21px, weight 800)
3. **Subheading**: "Gestión académica y trazabilidad · Regional Córdoba" (13px, muted)
4. **Campo Email**: input full-width, border-radius 11px, padding 11px 13px
5. **Campo Password**: idem, type password
6. **Botón Ingresar**: full-width, bg #4338ca, color #fff, border-radius 11px, padding 12px
7. **Aviso 2FA**: ícono shield + "Verificación en dos pasos habilitada para tu cuenta" (11.5px, muted)
8. **Divisor**: "o entrá a la demo como" (estilo eyebrow)
9. **Cards de rol**: una por rol, con avatar degradado + nombre + flecha → al click entra directo como ese rol

**Flujo 2FA** (pendiente de implementar): entre validación de credenciales y emisión de JWT, gate TOTP — input de 6 dígitos del authenticator. Ver C-03 en el backend.

---

### MIS MATERIAS (COORDINADOR)

**Archivo**: `proto/views-acad.jsx` → `VMaterias` (rama `role !== 'PROFESOR'`)

Layout: título + subtítulo → 4 KPIs → filtros + tabs → grid 2 columnas de cards.

**KPIs** (grid 4 cols, gap 14px):
- Materias a cargo, Alumnos totales, Alumnos atrasados (warn rojo), Tareas pendientes (vio)
- Cada KPI: chip de ícono 34px + número grande (26-27px weight 800) + label + sub
- Clickeables → navegan a la vista correspondiente (atrasados, tareas, monitor)

**Cards de materia** (grid 2 cols, gap 14px):
- Header: sigla (46px avatar cuadrado, degradado índigo claro) + nombre + carrera + badge de rol
- Meta-tags: cohorte, estado (estChip), vigencia, regional
- Stats row: alumnos / comisiones / docentes / atrasados (este último en rojo)
- Barra de avance: label "Avance del cuatrimestre" + porcentaje + bar
- Footer de acciones: 3 botones sm (Padrón pri, Calificar, Equipo)

---

### MIS MATERIAS (PROFESOR)

**Archivo**: `proto/views-acad.jsx` → `VMaterias` (rama `role === 'PROFESOR'`)

Grid 3 columnas de cards de comisión.  
Cada card: avatar con número de comisión + nombre materia + badge atrasados en rojo + barra de avance + 2 botones (Calificar pri, Atrasados).

---

### CALIFICACIONES — Flujo en 3 pasos (PROFESOR/COORDINADOR)

**Archivo**: `proto/views-acad.jsx` → `VCalif`

**Paso 1 — Importar**:
- ContextBar (selección de materia/cohorte/comisión)
- Dropzone: borde dashed 2px #d4d8e4, border-radius 14px, bg #fafbff
  - Ícono download 50px en índigo claro
  - Título "Importá las calificaciones del LMS"
  - Subtítulo con nota sobre columnas "(Real)"
  - Dos botones: "Simular importación" (pri) y "Sincronizar con LMS"

**Paso 2 — Preview de actividades**:
- Banner de éxito verde con nombre del archivo y stats
- Card "Actividades detectadas": lista de actividades con checkbox (Check), nombre y badge de escala (Numérica/Textual)
  - Escala Textual: color cyan (#0e7490 / #ecfeff)
- Card "Umbral": slider range (min 40, max 80, default 60), número grande en índigo, botón "Analizar N actividades" pri

**Paso 3 — Planilla**:
- 4 mini-KPIs: Promedio, Aprobados, Atrasados (rojo), Umbral
- Tabla: Alumno (avatar+nombre) | Legajo | Parcial 1 | Parcial 2 | TP Int. | Condición
  - Celdas de nota (`Score`): 34×28px, border-radius 7px; verde ≥6, amber 4-5, rojo <4; vacío = borde dashed
  - Badge de condición: Promociona (verde), Regular (índigo), Riesgo (rojo)
- Banner de alerta (fondo #fff7ed, border amber) con link a Atrasados

---

### ATRASADOS — Seleccionar y comunicar

**Archivo**: `proto/views-acad.jsx` → `VAtrasados`

- Tabla con checkbox por fila (selección múltiple, seleccionar-todos)
- Filas seleccionadas: bg #f5f6ff
- Botón "Comunicar a N seleccionados" en header se habilita cuando n > 0
- Modal "Comunicar a alumnos atrasados":
  - Editor de asunto + cuerpo con variables `{{nombre}}` etc. (chips en índigo claro, font monospace)
  - Toggle Vista previa / Editar
  - Aviso de aprobación (bg #fff7ed): "Por ser envío masivo, requiere aprobación de Coordinación (RN-17)"
  - Botones: Vista previa + Encolar envío (pri)

---

### PADRÓN — Importación con versionado

**Archivo**: `proto/views-acad.jsx` → `VPadron`  
**CORRECCIÓN**: El texto del warning debe decir: **"Importar una nueva versión del padrón desactiva la versión activa anterior de esta comisión (C-09 · VersionPadron)"**, NO "reemplaza por completo sin historial".

Elementos:
- ContextBar
- Banner de advertencia amber (no destructivo — es versionado)
- Dropzone con botón "Seleccionar archivo"
- Tabla del padrón activo actual

**Pendiente de agregar**: vista previa de la nueva versión antes de activarla (F1.3/F1.4 de C-09).

---

### SEGUIMIENTO

**Archivo**: `proto/views-acad.jsx` → `VSegui`

- Barra de filtros (buscar + comisión + mín. cumplidas + botón Filtrar)
- Tabla: Alumno | Comisión | Regional | Progreso (barra inline + "N/tot") | Última actividad | Estado
  - Colores de barra: verde para "Al día", amber para "Atrasado", rojo para "En riesgo"

---

### MONITOR (COORDINADOR/ADMIN)

**Archivo**: `proto/views-acad.jsx` → `VMonitor`

- Filtros en grid 4 cols: Materia (con opción "Todas las materias" — RN-29), Comisión, Regional, Buscar alumno
- Tabla similar a Seguimiento pero con columna "Cumplidas" (N/tot) numérica

---

### EQUIPOS DOCENTES

**Archivo**: `proto/views-gest.jsx` → `VEquipos`

- ContextBar (Materia + Cohorte + Comisión)
- Grid 1.7fr + 1fr:
  - Izquierda: tabla roster con avatar + nombre + comisiones + badge rol + badge estado
  - Derecha: panel "Asignación masiva" (chips de docentes seleccionados + buscador) + botón pri + card dashed "Clonar equipo" (clickeable, genera toast)

---

### APROBACIONES (COORDINADOR)

**Archivo**: `proto/views-gest.jsx` → `VAprob`

Estado interactivo: los lotes en cola tienen botones "Aprobar" (pri) y "Cancelar". Al aprobar → estado cambia a badge "Enviado". Al cancelar → badge "Cancelada". Toast de confirmación.

3 mini-KPIs: Pendientes de aprobar (amber) / Aprobados hoy (verde) / Cancelados (rojo).

---

### AVISOS (COORDINADOR/ADMIN)

**Archivo**: `proto/views-gest.jsx` → `VAvisos`

- Tabla de gestión + panel lateral "Mis avisos"
- Botón "Nuevo aviso" → modal con:
  - Campos: título, cuerpo, alcance (dropdown), severidad (segmented control: Info/Advertencia/Crítico), vigencia desde/hasta
  - Toggle "Requiere acuse de recibo" (con descripción RN-19)
  - Botón Publicar

**Colores de severidad**:
- Crítico: #e7515a / #fff1f0
- Advertencia: #d97706 / #fef6e7
- Info: #4338ca / #eef0ff

---

### AVISOS (ALUMNO) — con acuse de recibo

**Archivo**: `proto/views-alumno.jsx` → `AAvisos`

Cards verticales, una por aviso:
- Ícono de severidad (alert o bell) en color de severidad
- Título + badge severidad + cuerpo completo + metadatos (de + fecha)
- Footer condicional si `require_ack`:
  - Estado pendiente: texto "Requiere acuse de recibo" + botón "Confirmar lectura" (pri sm)
  - Estado confirmado: checkmark verde + "Lectura confirmada"

---

### COMUNICACIONES — Composer

**Archivo**: `proto/views-gest.jsx` → `VComuni`

Grid 1.5fr + 1fr:
- Izquierda: editor (asunto + cuerpo con variables {{nombre}} como chips inline + insertar variables)
- Derecha: destinatarios (audiencia selector + chips de comisiones) + card de "Antes de enviar" con nota sobre preview (RN-16) y aprobación (RN-17) + botones Previsualizar + Encolar

Modal de Vista previa: muestra el mensaje renderizado con datos de ejemplo.

---

### COLOQUIOS (ALUMNO) — Reservar turno

**Archivo**: `proto/views-alumno.jsx` → `AColoquios`

Estado interactivo complejo:
- Cards de convocatoria, dentro grid de turnos (días × horas)
- Cada turno: borde normal, cursor pointer si tiene cupos
  - Sin cupos: opacidad 0.6, cursor not-allowed, texto "Sin cupos" en gris
  - Con cupos: borde #e3e6ee, texto "N cupos" en índigo, hover
  - Turno propio (tras reservar): borde #16a34a, bg #ecfdf3, texto "✓ Tu turno" en verde
- Click en turno con cupos → Modal de confirmación → al confirmar: banner verde en top de página
- Banner: bg #ecfdf3, border #bbf3d0, ícono check blanco sobre bg verde, texto en #166534 + botón "Cancelar reserva"

---

### MI ESTADO (ALUMNO)

**Archivo**: `proto/views-alumno.jsx` → `AEstado`

- 4 KPIs: Materias / Al día (verde) / En riesgo (rojo) / Próxima evaluación (fecha, amber)
- Banner de alerta si hay materias en riesgo (bg #fff7ed) con botón "Reservar coloquio"
- Grid 2 cols de cards de materia:
  - Condición badge (Promociona/Regular/Riesgo)
  - Scores de P1 y P2 (número grande con color semántico)
  - Barra de avance
  - Footer: próxima fecha o alerta en amber

---

### LIQUIDACIONES (FINANZAS)

**Archivo**: `proto/views-admin.jsx` → `VLiquid`

4 KPIs: Total sin factura (verde) / Total con factura (amber) / Docentes (vio) / Estado (abierta/cerrada).

3 segmentos separados de tabla (RN-35/36):
1. "Detalle general (relación de dependencia)"
2. "NEXO · se muestra aparte pero suma al total"
3. "Docentes que facturan · excluidos del total"

Columnas: Docente | Rol | Comisiones | Base | Plus | Total

Botón "Cerrar liquidación" → Modal de confirmación → al confirmar: badge "Cerrada · inmutable" reemplaza el botón (estado inmutable, RN-22).

---

### FACTURAS (FINANZAS)

**Archivo**: `proto/views-admin.jsx` → `VFacturas`

Tabla: Docente | Período | Detalle | Archivo (link a PDF) | Estado | Acción
- Estado Pendiente → botón "Marcar abonada" (pri sm) → cambia a badge Pagado (verde), toast.

---

### GRILLA SALARIAL (FINANZAS)

**Archivo**: `proto/views-admin.jsx` → `VGrilla`

Grid 2 cols:
- Tabla "Salario base por rol": Rol | Monto | Vigencia
- Tabla "Plus por categoría × rol": Categoría (badge violeta) | Rol | Monto

---

### CONFIGURACIÓN DEL TENANT (ADMIN)

**Archivo**: `proto/views-admin.jsx` → `VConfig`

Grid 2 cols:
- Card "General": toggles interactivos (click cambia estado inmediatamente + toast)
  - "Aprobación de comunicaciones masivas" (RN-17)
  - "Verificación en dos pasos" 
  - "Umbral de aprobación por defecto" (solo lectura, badge con valor)
- Card "Escala de calificación textual": chips de valores aprobatorios (verde) vs no aprobatorios (gris) + info de marca

**Toggle**: 42×24px, bg índigo si on, bg gris si off. Círculo blanco 18×18px, transición left 3px→21px.

---

### ESTRUCTURA ACADÉMICA (ADMIN)

**Archivo**: `proto/views-admin.jsx` → `VEstructura`

Grid 2 cols:
- Árbol jerárquico: Regional → Carrera → Materia → (comisiones como count)
  - Profundidad = padding-left (12px + depth × 22px)
  - Ícono de expand/collapse (chevron) + ícono de entidad + label + count badge
  - Item activo: bg #eef0ff, color #4338ca, weight 800
- Panel de detalle de la entidad seleccionada (a la derecha):
  - Grid 2×2 de mini-tarjetas con propiedades
  - Lista de comisiones con avatar cuadrado + docente + count

---

### INBOX / MENSAJES

**Archivo**: `proto/views-gest.jsx` → `VInbox`

Layout de cliente de correo en 2 paneles:
- Izquierda (320px): lista de hilos — avatar + remitente + asunto + preview + fecha
  - Fila activa: bg #f5f6ff
- Derecha: detalle del hilo seleccionado — asunto + metadatos + cuerpo completo + input de respuesta + botón Responder

---

## Interacciones globales

| Acción | Comportamiento |
|--------|---------------|
| Click en nav item | Navega a la vista (key por role+view para re-montar) |
| Role switcher | Abre dropdown, seleccionar cambia nav+home |
| Logout | Vuelve al login |
| Botón bell | Toast "No hay notificaciones nuevas" (placeholder) |
| Cualquier acción secundaria sin formulario | Toast descriptivo del 1.4s |
| Modal open | Overlay animado, click fuera cierra |
| Toast | Auto-desaparece a los 2800ms |

---

## Pendientes de implementar en el prototipo (correcciones para C-24)

Estas vistas/flujos están documentados y tienen backend implementado pero **faltan en el prototipo HTML actual**. Claude Code debe implementarlas directamente en el frontend TypeScript:

1. **Perfil propio** (`/perfil`): editar nombre, CBU/alias, datos fiscales, modalidad de cobro. CUIL solo lectura. Ver C-20 backend.
2. **Flujo TOTP de 2FA**: gate entre validación de credenciales y emisión de sesión — input de 6 dígitos. Ver C-03 backend.
3. **Vista previa de padrón** antes de activar (F1.3/F1.4 de C-09): después del dropzone, mostrar preview de la nueva versión con diff de cambios antes del botón "Activar padrón".
4. **Formulario de encuentro recurrente**: día de semana + hora + desde/hasta + cantidad de semanas → genera N instancias. Ver C-13 backend (RN-13).
5. **Hilo de comentarios en Tareas**: detalle de tarea con `ComentarioTarea`, cambio de estado, timeline de actividad. Ver C-16 backend.
6. **Impersonación**: banner superior naranja cuando un ADMIN está impersonando a otro usuario — "Estás viendo como [nombre] · [botón Finalizar impersonación]". Ver C-05 backend.

---

## Archivos de referencia incluidos en este paquete

| Archivo | Contenido |
|---------|-----------|
| `Activia Prototipo.html` | **Prototipo interactivo principal** — abrir en navegador, usar el switcher de roles |
| `proto/core.jsx` | Datos de prueba, shell interactivo, role switcher, modal, toasts |
| `proto/views-acad.jsx` | Vistas académicas (materias, calificaciones con flujo 3 pasos, atrasados, padrón, seguimiento, monitor) |
| `proto/views-gest.jsx` | Gestión y comunicación (equipos, aprobaciones, avisos, comunicaciones, tareas, encuentros, guardias, coloquios, setup, auditoría, inbox) |
| `proto/views-alumno.jsx` | Vistas del alumno (estado, materias, coloquios con reserva, avisos con ack) |
| `proto/views-admin.jsx` | Admin y finanzas (usuarios, estructura, fechas, programas, config, liquidaciones, historial, grilla, facturas) |
| `proto/app.jsx` | Login, router por rol, toasts, app root |
| `screens/shell-a.jsx` | Sistema de CSS custom (NO copiar clases — recrear en Tailwind) + primitivos React |
| `screens/shared.jsx` | Datos de dominio + componente Icon (SVG paths de Feather Icons) |
| `docs/analisis-documentacion.md` | Análisis completo del PDF (120 págs) → reglas de negocio, entidades, flujos |
| `docs/analisis-changes.md` | Análisis del CHANGES.md → qué está implementado, gaps, correcciones |

---

## Cómo usar este paquete

1. **Abrí `Activia Prototipo.html`** en Chrome/Safari — interactuá con el prototipo completo.
2. **Leé `docs/analisis-changes.md`** para entender el estado actual del repo y los gaps.
3. **Implementá en el repo real** (`frontend/`) usando el stack TypeScript existente y los endpoints del backend.
4. **Para C-24**: los componentes de Finanzas y Admin del prototipo son la referencia visual directa.
5. **Para las 6 correcciones**: ver sección "Pendientes" arriba — tienen backend listo para conectar.

---

*Generado el 2026-06-06 · activia-trace design handoff v1*
