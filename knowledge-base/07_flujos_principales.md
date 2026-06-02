# 07 — Flujos Principales

> **Propósito**: describir los flujos extremo a extremo más relevantes del sistema, en términos de dominio (actor → acción → resultado). Cada flujo es una secuencia de pasos de negocio que un equipo puede implementar en cualquier arquitectura o stack. Los detalles técnicos de autenticación, sesiones y seguridad viven en [`docs/ARQUITECTURA.md` §5](../docs/ARQUITECTURA.md).

---

## FL-01 — Autenticación

**Flujo principal (login):**

1. El usuario accede a la pantalla de inicio de sesión del sistema.
2. Ingresa su **email** y **contraseña**.
3. El sistema valida las credenciales contra el registro del tenant correspondiente.
4. Si son válidas, el sistema emite una **sesión autenticada** (token de acceso de vida corta + token de refresco con rotación). La identidad del usuario, sus roles y su tenant quedan **exclusivamente en la sesión** — ningún dato de la petición puede alterarlos.
5. El usuario accede al sistema y el menú/interfaz se adapta a los permisos de su sesión.
6. Cuando el usuario cierra sesión, la sesión se invalida y los tokens quedan revocados.

**Variante 2FA (opcional por configuración del tenant):**

- Luego del paso 3 y antes del paso 4, el sistema exige un segundo factor (TOTP u otro mecanismo configurable).
- Si el segundo factor no se supera, la sesión no se emite.

**Flujo de recuperación de contraseña:**

1. El usuario solicita recuperar su contraseña indicando su **email**.
2. El sistema genera un **token de un solo uso** y lo envía al email registrado.
3. El usuario sigue el enlace del email y establece una nueva contraseña.
4. El token queda invalidado tras su uso o por vencimiento.

> 🔑 **Regla de oro**: la identidad y el tenant del usuario salen **exclusivamente de la sesión autenticada**. Ningún parámetro de la URL, campo de formulario ni encabezado puede cambiar quién es el usuario ni qué permisos tiene. Ver modelo de seguridad completo en [03 — Actores y Roles §1](03_actores_y_roles.md) y en [`docs/ARQUITECTURA.md` §5](../docs/ARQUITECTURA.md).

---

## FL-02 — Importar calificaciones y detectar alumnos atrasados (flujo central del PROFESOR)

Este es el flujo de mayor uso del sistema para el rol PROFESOR. Permite analizar el estado académico de una comisión a partir de los datos exportados del LMS.

1. **Inicio de sesión**: el PROFESOR inicia sesión y accede a la gestión de su comisión (materia + período).

2. **Selección de comisión**: selecciona la materia y cohorte que quiere analizar. La vista muestra todas las secciones de trabajo disponibles.

3. **Importación de calificaciones** (`calificaciones:importar`):
   - El PROFESOR sube el archivo exportado del LMS con las calificaciones de la comisión.
   - El sistema procesa el archivo, detecta las columnas de actividades con valores reales numéricos ([RN-01]) y los valores textuales como "aprobada", "no entregado", etc. ([RN-02]).
   - El sistema muestra una lista de actividades detectadas para que el PROFESOR seleccione cuáles incluir en el análisis.

4. **Configuración del umbral** (`calificaciones:importar`):
   - El PROFESOR establece el umbral de aprobación en porcentaje (valor por defecto: 60 % [RN-03]).
   - Confirma la configuración.

5. **Cómputo automático**: el sistema calcula y presenta:
   - Alumnos atrasados: los que tienen actividades faltantes o calificación por debajo del umbral ([RN-06]).
   - Ranking de actividades aprobadas ([RN-09]).
   - Reportes rápidos de estado por comisión.
   - Notas finales agrupadas.

6. **Detección de entregas sin corregir** (opcional, `atrasados:ver`):
   - El PROFESOR sube el reporte de finalización de actividades del LMS.
   - El sistema cruza ese reporte con las calificaciones y genera la tabla "posibles entregas sin corregir" ([RN-07], [RN-08]).
   - Se puede exportar un listado de esas entregas para seguimiento externo.

7. **Comunicación con alumnos atrasados** (`comunicacion:enviar`):
   - El PROFESOR selecciona uno o más alumnos atrasados.
   - El sistema genera una previsualización del mensaje (asunto + cuerpo) personalizado por alumno.
   - El PROFESOR confirma el envío.
   - Cada mensaje ingresa a la cola de envío en estado **Pendiente** ([RN-15]).

8. **Despacho de mensajes** (proceso asincrónico del sistema):
   - Los mensajes Pendientes pasan a estado **Enviando**, y luego a **OK**, **Fallido** o **Cancelado** según el resultado ([RN-15]).

**Auditoría**: los pasos 3, 4, 6 y 7 generan un registro en el log de auditoría ([RN-23](05_reglas_de_negocio.md#rn-23)).

---

## FL-03 — Setup de inicio de cuatrimestre (COORDINADOR)

Flujo que el COORDINADOR ejecuta al comienzo de cada período académico para preparar la estructura del nuevo cuatrimestre.

1. **Crear la nueva cohorte** (`estructura:gestionar`):
   - Define el identificador, nombre, fechas de vigencia (inicio y fin del período).

2. **Clonar el equipo docente** (`equipos:asignar`):
   - Selecciona un equipo docente de un período anterior (materia × carrera × cohorte origen).
   - Selecciona el destino (misma materia × carrera × nueva cohorte).
   - El sistema duplica todas las asignaciones vigentes con las fechas del nuevo período ([RN-12]).

3. **Ajuste de asignaciones** (`equipos:asignar`):
   - El COORDINADOR completa las asignaciones faltantes (docentes nuevos, materias sin asignar).
   - Puede usar la operación de alta masiva para asignar varios docentes de una sola vez ([F4.4]).

4. **Ajuste de vigencias** (`equipos:asignar`):
   - Modifica las fechas de vigencia del equipo si el período difiere del estándar.

5. **Carga de programas de materia** (`estructura:gestionar`):
   - Sube los documentos de programa actualizados para cada materia × cohorte.

6. **Carga de fechas de evaluaciones** (`estructura:gestionar`):
   - Registra las fechas de parciales, trabajos prácticos y coloquios del nuevo cuatrimestre.

7. **Publicar aviso de bienvenida** (`avisos:publicar`):
   - Crea un aviso con alcance a la nueva cohorte, dirigido a todos los roles, anunciando el inicio del período.

8. **Importación del padrón inicial** (`padron:importar`):
   - Cuando comienza el cursado, importa el listado de alumnos y actividades del período.

---

## FL-04 — Envío masivo de recordatorios con aprobación

Flujo para comunicaciones a escala que requieren una etapa de revisión antes del despacho efectivo.

**Parte A — Generación (PROFESOR):**

1. El PROFESOR importa las calificaciones de su comisión ([FL-02], pasos 3–5).
2. El sistema identifica los alumnos atrasados del período.
3. El PROFESOR dispara el envío masivo de recordatorios.
4. Cada mensaje ingresa a la cola en estado **Pendiente** (`comunicacion:enviar`).

**Parte B — Aprobación (COORDINADOR o rol con `comunicacion:aprobar`):**

5. El aprobador accede a la cola de mensajes pendientes.
6. Aprueba el lote completo o lo cancela (también puede aprobar o cancelar por destinatario individual).
7. Los mensajes aprobados pasan a estado **Enviando** → el sistema los despacha → quedan en **OK** o **Fallido**.
8. Los mensajes cancelados quedan en estado **Cancelado**.

**Parte C — Seguimiento (PROFESOR / COORDINADOR):**

9. El panel de estado de comunicaciones muestra el resultado por materia y destinatario (OK / Fallido / Cancelado).

---

## FL-05 — Workflow de Tareas (coordinación ↔ docente)

Flujo de coordinación interna mediante tareas asignadas entre roles.

**Alta de tarea (COORDINADOR):**

1. El COORDINADOR crea una tarea: define la materia asociada, el docente asignado, descripción y criterio de cierre.
2. La tarea queda en estado **Abierta** y aparece en el panel del docente asignado.

**Gestión de la tarea (PROFESOR / TUTOR):**

3. El docente ve la tarea asignada en su panel.
4. Actualiza el estado (en progreso, completada, etc.) según avanza.
5. Puede agregar comentarios o evidencias al hilo de la tarea.

**Revisión y cierre (COORDINADOR):**

6. El COORDINADOR filtra las tareas por estado, materia o docente y lee los comentarios.
7. Aprueba el cierre de la tarea o la devuelve al docente para ajustes con una observación.

> ℹ️ Este es un módulo de **alto uso**: la plataforma gestiona varios cientos de tareas en simultáneo durante el período activo.

---

## FL-06 — Encuentros recurrentes con grabaciones

Flujo para planificar, registrar y publicar los encuentros sincrónicos de una comisión.

**Planificación (PROFESOR):**

1. El PROFESOR accede al módulo de encuentros de su comisión.
2. Crea una serie recurrente: define materia, día de la semana, horario, fecha de inicio y cantidad de semanas.
3. El sistema genera automáticamente todas las instancias de la serie ([RN-13]).

**Registro posterior a cada encuentro (PROFESOR):**

4. El PROFESOR accede a la instancia del día.
5. Marca el encuentro como realizado y pega la URL del video grabado.

**Supervisión (COORDINADOR):**

6. El COORDINADOR accede a la vista de administración del módulo y audita qué encuentros se realizaron y cuáles no.

**Exportación para el LMS (PROFESOR):**

7. El sistema genera un bloque HTML con el calendario de encuentros y sus grabaciones.
8. El PROFESOR copia ese bloque y lo embebe en el aula virtual del LMS (acción manual fuera del sistema).

---

## FL-07 — Coloquio: convocatoria a evaluación

Flujo para convocar a alumnos a una instancia de evaluación final y gestionar las reservas de turnos.

**Preparación (PROFESOR):**

1. El PROFESOR importa el padrón de candidatos al coloquio (alumnos habilitados).
2. Crea la convocatoria: define materia, nombre de la instancia (ej. "Coloquio Final"), días disponibles y cupos por día.
3. El sistema crea los turnos reservables con sus cupos.

**Reserva de turno (ALUMNO):**

4. Los alumnos habilitados ven la convocatoria y reservan su turno en un día disponible con cupo.

**Seguimiento (PROFESOR / COORDINADOR):**

5. La vista de la convocatoria muestra: convocados, reservas realizadas y cupos libres.
6. El COORDINADOR accede a la agenda consolidada de reservas activas de todas las comisiones.
7. El COORDINADOR puede consultar el registro académico consolidado con las notas finales de coloquio.

---

## FL-08 — Liquidación de honorarios

Flujo exclusivo del rol FINANZAS para calcular y cerrar las liquidaciones de honorarios docentes.

1. **Selección de período** (`liquidaciones:calcular`): el usuario FINANZAS selecciona el período a liquidar.
2. **Cálculo automático**: el sistema calcula por docente:
   - Monto base (según la grilla salarial del rol).
   - Plus por comisiones adicionales.
   - Total = Base + Plus ([RN-21]).
3. **Vista previa** (`liquidaciones:ver`): el usuario verifica la tabla antes de cualquier acción irreversible.
4. **Exportación** (`liquidaciones:exportar`): genera la planilla de liquidación para uso externo (pago o presentación).
5. **Cierre de liquidación** (`liquidaciones:cerrar`): el período queda **inmutabilizado** — no puede modificarse ([RN-22]).
6. **Historial** (`liquidaciones:ver`): consulta y audita liquidaciones de períodos anteriores.

---

## FL-09 — Publicación de aviso del sistema

Flujo para comunicar novedades institucionales a grupos de usuarios de forma controlada.

**Creación del aviso (COORDINADOR o ADMIN):**

1. El publicador accede al módulo de avisos y completa el formulario:
   - **Alcance**: global, por materia o por cohorte.
   - **Contexto**: materia y/o cohorte específica si el alcance no es global.
   - **Roles destinatarios**: a qué roles se muestra el aviso.
   - **Severidad**: informativo, advertencia, urgente, etc.
   - **Contenido**: título y cuerpo del aviso (puede contener formato enriquecido).
   - **Ventana de visibilidad**: fecha/hora de inicio y fin de la publicación.
   - **Orden de prioridad**: para controlar qué aviso aparece primero si hay varios activos.
   - **Estado activo/inactivo**: permite preparar el aviso antes de publicarlo.
   - **Requiere confirmación**: si los destinatarios deben acusar recibo del aviso.
2. Publica el aviso.

**Visualización por los destinatarios:**

3. Al acceder al sistema o navegar, los usuarios ven los avisos que coinciden con su rol, alcance y cohorte ([RN-20]).
4. Si el aviso requiere confirmación (`require_ack = true`), el usuario debe acusar recibo para que el aviso deje de mostrarse y el contador de confirmaciones se incremente.
5. Un aviso fuera de su ventana de visibilidad no se muestra, aunque siga existiendo en el sistema ([RN-18]).

---

## FL-10 — Mensajería interna entre usuarios del sistema

Flujo de comunicación interna entre roles del sistema (distinto de los emails automáticos a alumnos).

**Generación del mensaje (Sistema / otro usuario):**

1. El sistema o un usuario con permisos genera un mensaje hacia el inbox de un docente u otro rol: puede ser un aviso personalizado, una notificación de coordinación o una respuesta de un alumno.

**Gestión del inbox (PROFESOR / destinatario):**

2. El destinatario accede a su inbox y ve los hilos activos.
3. Abre un mensaje para leerlo.
4. Responde con asunto y cuerpo de respuesta si la conversación lo permite.
5. Envía la respuesta, que se agrega al hilo.

> ℹ️ Este módulo es **paralelo** al sistema de emails a alumnos: los emails a alumnos son comunicaciones salientes del sistema hacia externos; el inbox interno es la mensajería entre usuarios registrados del sistema.

---

## FL-11 — Auditoría de actividad por docente (panel de supervisión)

Flujo para que COORDINADOR o ADMIN supervisen la actividad de los docentes en el sistema.

1. El supervisor accede al panel de auditoría (`auditoria:ver`).
2. Aplica filtros: rango de fechas, materia, usuario, estado de actividad (activo/inactivo).
3. El sistema presenta:
   - **Acciones por día**: serie temporal de actividad por usuario.
   - **Estado de comunicaciones**: distribución de estados (Pendiente / Enviando / OK / Fallido / Cancelado) por docente y materia.
   - **Interacciones por docente y materia**: métricas detalladas de uso de las funcionalidades.
   - **Registro de últimas acciones**: log detallado con fecha, hora, acción, IP y agente de usuario (limitado a un máximo configurable de registros por consulta).
4. El supervisor identifica docentes inactivos o con comunicaciones fallidas y toma acción (mensaje directo, reasignación, etc.).

---

## FL-12 — Configuración inicial del sistema (primer ADMIN del tenant)

Flujo para la puesta en marcha de un nuevo tenant en el sistema.

1. Un operador autorizado del sistema crea el tenant con su identificador y configuración base.
2. Se provisionan las credenciales del primer usuario ADMIN del tenant.
3. El ADMIN inicial configura la estructura académica: carreras, cohortes, materias.
4. El ADMIN crea los primeros usuarios del tenant y asigna roles.
5. El ADMIN configura la grilla salarial base y los parámetros de notificaciones.
6. El sistema queda listo para operar el primer período académico.

---

## Consideraciones generales para implementadores

- **Identidad desde la sesión**: en todo flujo, la identidad del actor, su tenant y sus permisos se resuelven desde la sesión autenticada. Ningún parámetro externo puede suplantarlos. Ver [03 — Actores y Roles §1](03_actores_y_roles.md).
- **Auditoría**: toda acción significativa (importaciones, envíos, cambios de estado, cierres) genera un registro de auditoría con actor, acción, timestamp y contexto ([RN-23](05_reglas_de_negocio.md#rn-23)).
- **Colas asincrónicas**: los envíos de mensajes y el despacho de comunicaciones masivas operan de forma asincrónica. Los estados de transición (Pendiente → Enviando → OK / Fallido / Cancelado) son parte del modelo de dominio ([RN-15]).
- **Multi-tenant**: toda operación está acotada al tenant del usuario autenticado. No existe ningún flujo que cruce datos entre tenants.
