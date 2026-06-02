# 01 — Visión y Objetivos

> **Propósito**: definir QUÉ es el sistema, por qué existe y qué valor entrega a cada actor. Escrito en lenguaje de dominio, agnóstico de tecnología. Describe la visión de producto a construir, no una implementación concreta. El detalle de arquitectura y stack vive en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

---

## 1. Definición del producto

**Activia-Trace** es una **plataforma de gestión académica y trazabilidad de actividades estudiantiles** que actúa como capa de orquestación sobre un LMS institucional (típicamente Moodle). Resuelve el problema de que un LMS estándar, por sí solo, no permite:

- Consolidar calificaciones de múltiples actividades en una vista accionable.
- Detectar y comunicar atrasos a alumnos de forma masiva y personalizada.
- Coordinar equipos docentes (asignaciones, vigencias, jerarquías) a través de comisiones.
- Operar liquidaciones de honorarios contra la actividad efectiva del docente.
- Trazar con precisión quién hizo qué, cuándo y sobre qué dato académico.

El sistema **no reemplaza** al LMS: lo complementa. El LMS sigue siendo el repositorio de entregas y material didáctico; Activia-Trace es el motor de inteligencia, coordinación y trazabilidad que opera sobre los datos que el LMS produce.

---

## 2. Visión de producto

> Que cualquier institución académica pueda conocer, en tiempo real, el estado de avance de cada alumno en cada materia, y que los actores responsables cuenten con las herramientas para intervenir de forma oportuna — sin fricciones operativas ni dependencia de procesos manuales.

La plataforma apunta a ser **multi-tenant**: cada institución opera en un espacio completamente aislado, con su propia estructura académica, equipos y configuración.

---

## 3. Objetivos por actor

### 3.1 ALUMNO

- Consultar su propio estado académico: calificaciones, entregas pendientes, situación de atraso.
- Reservar instancias de evaluación (coloquios, recuperatorios) dentro de los cupos disponibles.
- Recibir comunicaciones personalizadas del equipo docente.
- Confirmar lectura de avisos institucionales.

> El alumno es **usuario activo** del sistema, no un mero objeto de observación. Tiene acceso a su propia información y puede realizar acciones dentro de su contexto. Toda interacción con el contenido didáctico ocurre en el LMS; Activia-Trace gestiona el seguimiento y la comunicación.

### 3.2 TUTOR

- Acompañar el seguimiento de alumnos bajo su supervisión.
- Ver alumnos con atrasos o entregas pendientes de corrección en las comisiones asignadas.
- Cubrir guardias y registrar su participación en encuentros.
- Asistir al PROFESOR en la gestión de su comisión.

### 3.3 PROFESOR

- Importar registros de calificaciones exportados del LMS por materia y comisión.
- Detectar alumnos atrasados (sin entrega o con nota por debajo del umbral configurable).
- Detectar trabajos prácticos entregados pero aún sin corregir.
- Enviar recordatorios personalizados a alumnos, con previsualización del contenido antes del envío.
- Registrar encuentros sincrónicos (slots semanales e instancias puntuales).
- Llevar registro de guardias realizadas.
- Recibir y responder mensajes internos.
- Gestionar tareas asignadas por la coordinación.

### 3.4 COORDINADOR

- Gestionar el padrón completo de docentes del tenant (alta, datos, estado activo/inactivo).
- Asignar docentes a materias × carrera × cohorte × comisión, en forma individual o masiva.
- Definir la estructura académica: carreras, cohortes, programas, fechas de evaluaciones.
- Operar el monitor general de actividades para detectar alumnos en riesgo a escala institucional.
- Publicar avisos segmentados por materia, cohorte o rol, con nivel de severidad configurable.
- Auditar las acciones de cada docente en su área de responsabilidad.
- Clonar equipos docentes entre cohortes para acelerar el setup de inicio de período.

### 3.5 ADMIN

- Administrar la configuración global del tenant.
- Gestionar usuarios, roles y permisos dentro de la institución.
- Gestionar la estructura académica completa (carreras, cohortes, materias).
- Auditar acciones de cualquier actor dentro del tenant.
- Operar todas las capacidades del sistema en modo de supervisión.

### 3.6 FINANZAS

- Calcular y cerrar liquidaciones de honorarios por docente, con base y plus configurable.
- Mantener y operar la grilla salarial del tenant.
- Gestionar facturas y exportar información de liquidaciones.
- Ver auditoría de acciones relacionadas con el módulo financiero.

---

## 4. Alcance funcional — lo que el sistema hace

| # | Capacidad | Descripción |
|---|-----------|-------------|
| 1 | **Ingesta de datos desde el LMS** | Importación de registros de calificaciones, registros de finalización de actividades y padrón de participantes exportados del LMS. |
| 2 | **Consolidación y análisis académico** | Rankings, detección de alumnos atrasados, entregas sin corregir, cálculo de notas finales agrupadas por comisión. |
| 3 | **Comunicación saliente** | Mensajes personalizados por alumno con previsualización antes del envío; flujo de aprobación para comunicaciones masivas. |
| 4 | **Gestión de equipos docentes** | ABM de docentes, asignaciones masivas, vigencias por contrato, clonado entre períodos. |
| 5 | **Calendario académico** | Fechas de evaluaciones parciales, trabajos prácticos, coloquios y encuentros recurrentes. |
| 6 | **Avisos institucionales** | Tablón con segmentación por rol, materia, cohorte y nivel de severidad; acuse de recibo por actor. |
| 7 | **Coloquios y evaluaciones** | Convocatorias, reserva de instancias con cupos limitados, registro consolidado de resultados. |
| 8 | **Liquidaciones de honorarios** | Cálculo base + plus por docente, exportación de resúmenes. |
| 9 | **Tareas internas** | Workflow entre PROFESOR y COORDINADOR con comentarios, estados y seguimiento. |
| 10 | **Auditoría** | Registro de toda acción significativa: actor, acción, dato afectado, timestamp, origen de la petición. |

---

## 5. Fuera de alcance — lo que el sistema NO hace

- **No es un LMS**: no aloja material didáctico ni recibe entregas de trabajos; eso vive en el LMS institucional.
- **No corrige automáticamente**: la corrección asistida por IA es un módulo externo que se integra a través de una API definida; no es parte del núcleo de Activia-Trace.
- **No gestiona inscripciones de alumnos**: las comisiones y matrículas se importan desde el LMS o desde el sistema de gestión institucional.
- **No emite certificados ni títulos**: el registro académico es consolidación de calificaciones, no un sistema de emisión de documentos oficiales.

---

## 6. Supuestos de producto (no negociables)

Estos supuestos están ya decididos y deben respetarse en cualquier implementación:

1. **Multi-tenant**: cada institución es un tenant completamente aislado; sus datos jamás se cruzan con los de otra institución.
2. **RBAC con permisos finos**: la autorización se basa en capacidades atómicas (`modulo:accion`), no en flags binarios. Ver [03 — Actores y Roles](03_actores_y_roles.md).
3. **Identidad desde la sesión, jamás desde la petición**: la identidad, los roles y el tenant de un usuario se derivan exclusivamente de su sesión autenticada. Ningún parámetro externo puede alterar quién es el usuario ni qué permisos tiene.
4. **Auditoría completa**: toda acción significativa queda registrada con trazabilidad de actor, contexto y tiempo.

---

## 7. Indicadores de valor (north star)

El sistema entrega valor medible cuando:

- Un COORDINADOR puede detectar alumnos en riesgo académico a escala institucional sin intervención manual.
- Un PROFESOR puede completar el ciclo completo (importar → analizar → comunicar) en una sesión de trabajo acotada.
- La tasa de alumnos sin respuesta a comunicaciones de atraso disminuye por efecto de la personalización y el seguimiento sistemático.
- El cierre de liquidaciones mensuales no requiere cálculos manuales fuera del sistema.
- El equipo de soporte puede auditar cualquier acción ocurrida en el sistema sin depender del recuerdo de los actores involucrados.
