# 11 — Historias de Usuario

> **Propósito**: describir los requerimientos del sistema desde la perspectiva de cada actor, en formato Connextra (Como / Quiero / Para) con criterios de aceptación (CA). Es agnóstico de tecnología: describe QUÉ debe hacer el sistema, no CÓMO se implementa. El detalle técnico de implementación vive en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md). Las reglas de negocio referenciadas están en [05 — Reglas de Negocio](05_reglas_de_negocio.md) y las capacidades en [06 — Funcionalidades](06_funcionalidades.md).

**Convenciones**:
- ID `HU-XX` para cada historia. Los códigos son estables y se usan como referencia cruzada entre archivos.
- Prioridad: 🔴 Alta · 🟡 Media · 🟢 Baja.
- Estado: ✅ Definida · 🔧 Parcialmente especificada · ❓ Pendiente de detalle.

---

## Épica 1 — Ingesta de Datos desde el LMS

### HU-01 🔴 ✅ — Importar calificaciones por materia
**Como** PROFESOR
**Quiero** subir el archivo de calificaciones exportado del LMS correspondiente a mi materia
**Para** consolidar todas las notas de las actividades en un solo lugar y poder analizarlas.

**CA**:
- Debo poder seleccionar la materia antes de iniciar la importación.
- El sistema acepta el formato estándar de exportación del LMS (planilla de cálculo).
- Al solicitar "previsualización" veo la lista de actividades detectadas y elijo cuáles analizar.
- Las columnas de nota numérica se interpretan como nota redondeada ([RN-01](05_reglas_de_negocio.md#rn-01)).
- Los valores cualitativos ("Satisfactorio", "Supera lo esperado") se almacenan como nota textual y cuentan como aprobado ([RN-02](05_reglas_de_negocio.md#rn-02)).
- La acción queda registrada en el registro de auditoría ([RN-23](05_reglas_de_negocio.md#rn-23)).

→ Ref: [F1.1](06_funcionalidades.md#f11--importar-planilla-de-calificaciones-por-materia)

---

### HU-02 🔴 ✅ — Detectar entregas finalizadas sin corregir
**Como** PROFESOR
**Quiero** subir el reporte de finalización de actividades del LMS
**Para** que el sistema me marque qué trabajos están entregados pero todavía no califiqué.

**CA**:
- El sistema acepta los formatos de exportación estándar del LMS.
- Se obtiene una tabla "Posibles TPs sin corregir" agrupada por actividad.
- Solo se listan actividades de escala textual ([RN-08](05_reglas_de_negocio.md#rn-08)).
- Puedo exportar la tabla resultante.
- Si no hay pendientes, se muestra un mensaje confirmatorio.

→ Ref: [F1.2](06_funcionalidades.md#f12--importar-reporte-de-finalización-para-detectar-tp-sin-corregir), [RN-07](05_reglas_de_negocio.md#rn-07)

---

### HU-03 🟡 ✅ — Importar padrón de alumnos por materia
**Como** PROFESOR
**Quiero** cargar el padrón de participantes exportado del LMS para una materia
**Para** tener la lista actualizada de alumnos contra la cual cruzar las actividades.

**CA**:
- Selecciono la materia antes de importar.
- El sistema toma Nombre, Apellido(s), Email y Grupos del archivo.
- La nueva carga reemplaza el padrón anterior para esa materia — no hay merge ([RN-05](05_reglas_de_negocio.md#rn-05)).
- Recibo confirmación visible del resultado de la importación.

→ Ref: [F1.3](06_funcionalidades.md#f13--importar-padrón-de-alumnos)

---

### HU-04 🟡 ✅ — Vaciar mis datos de una materia
**Como** PROFESOR
**Quiero** borrar mis datos de una materia específica
**Para** poder empezar de cero sin afectar a los otros docentes asignados a esa misma materia.

**CA**:
- El borrado afecta exclusivamente a la combinación (mi usuario, materia seleccionada), no a otros docentes ([RN-04](05_reglas_de_negocio.md#rn-04)).
- Se muestra una leyenda explicativa antes de solicitar confirmación.
- La acción requiere confirmación explícita.

→ Ref: [F1.5](06_funcionalidades.md#f15--vaciar-datos-por-materia)

---

## Épica 2 — Análisis y Reportes Académicos

### HU-05 🔴 ✅ — Configurar umbral de aprobación por materia
**Como** PROFESOR
**Quiero** definir el umbral porcentual para considerar a un alumno como atrasado
**Para** ajustar el criterio a las pautas pedagógicas de cada materia.

**CA**:
- El valor por defecto es 60% ([RN-03](05_reglas_de_negocio.md#rn-03)).
- La configuración se guarda por (usuario docente, materia).
- El cambio impacta inmediatamente en la sección "Estudiantes atrasados" y en los rankings.

→ Ref: [F2.1](06_funcionalidades.md#f21--configurar-umbral-por-materia)

---

### HU-06 🔴 ✅ — Ver lista de alumnos atrasados
**Como** PROFESOR
**Quiero** ver qué alumnos están atrasados (sin entregas o con nota por debajo del umbral)
**Para** decidir a quiénes enviar recordatorios.

**CA**:
- La vista muestra cantidad de alumnos y la tabla detallada.
- Definición de atrasado: ausencia de entrega o nota inferior al umbral configurado ([RN-06](05_reglas_de_negocio.md#rn-06)).
- Si no hay atrasados se muestra un mensaje positivo de confirmación.

→ Ref: [F2.2](06_funcionalidades.md#f22--visualizar-estudiantes-atrasados)

---

### HU-07 🟡 ✅ — Ver ranking de alumnos por actividades aprobadas
**Como** PROFESOR
**Quiero** un ranking de alumnos por cantidad de actividades aprobadas
**Para** identificar quiénes están más adelantados y quiénes necesitan apoyo.

**CA**:
- Solo se listan alumnos con al menos 1 actividad aprobada ([RN-09](05_reglas_de_negocio.md#rn-09)).
- Si no hay datos suficientes se muestra un mensaje aclaratorio.

→ Ref: [F2.3](06_funcionalidades.md#f23--ranking-de-aprobadas)

---

### HU-08 🟡 ✅ — Generar notas finales agrupadas para exportación
**Como** PROFESOR
**Quiero** definir agrupaciones de actividades para producir la nota final del alumno
**Para** exportar el reporte oficial de la materia.

**CA**:
- Puedo configurar qué actividades integran cada grupo.
- El resultado es exportable como planilla de cálculo.
- Si no hay actividades configuradas se muestra un mensaje orientador.

→ Ref: [F2.5](06_funcionalidades.md#f25--notas-finales-agrupación-para-exportación)

---

### HU-09 🟡 ✅ — Filtrar monitor general de alumnos
**Como** COORDINADOR
**Quiero** filtrar el monitor general por materia, regional, comisión, búsqueda libre y estado
**Para** ubicar rápidamente a alumnos en riesgo a nivel institucional.

**CA**:
- Los filtros producen una URL compartible (estado de la vista en la URL).
- La acción "Exportar" descarga la vista filtrada.
- Existe un panel de criterios de clasificación para ajustar reglas (→ [PA-11](10_preguntas_abiertas.md#pa-11)).

→ Ref: [F2.7](06_funcionalidades.md#f27--monitor-general-de-alumnos-vista-coordinador)

---

## Épica 3 — Comunicación con Alumnos

### HU-10 🔴 ✅ — Previsualizar un correo antes de enviarlo
**Como** PROFESOR
**Quiero** ver el asunto y el cuerpo renderizado de cada correo antes del envío
**Para** evitar errores de formato o variables sin reemplazar.

**CA**:
- Se muestra una previsualización con render real del cuerpo del mensaje.
- El correo no se envía hasta que confirmo desde la previsualización ([RN-16](05_reglas_de_negocio.md#rn-16)).

→ Ref: [F3.1](06_funcionalidades.md#f31--preview-del-correo-antes-de-enviar)

---

### HU-11 🔴 ✅ — Enviar recordatorios masivos a alumnos atrasados
**Como** PROFESOR
**Quiero** disparar un envío masivo a todos los alumnos atrasados detectados
**Para** comunicar su estado y motivar la regularización sin redactar mensajes individuales.

**CA**:
- Los mensajes ingresan a la cola en estado pendiente ([RN-15](05_reglas_de_negocio.md#rn-15)).
- Cada mensaje es personalizado por alumno.
- Puedo ver el conteo de estados (pendiente / enviado / fallido / cancelado) en el panel de interacciones.

→ Ref: [F3.2](06_funcionalidades.md#f32--envío-masivo-con-cola)

---

### HU-12 🔴 ✅ — Aprobar envíos masivos antes del despacho
**Como** usuario con el permiso `comunicacion:aprobar`
**Quiero** revisar y aprobar la cola de correos pendientes
**Para** evitar envíos accidentales o no autorizados desde la institución.

**CA**:
- El acceso está restringido a quienes tienen el permiso `comunicacion:aprobar` ([03 — Actores y Roles](03_actores_y_roles.md)).
- Los usuarios sin ese permiso no pueden alcanzar esta funcionalidad.
- Al aprobar, el mensaje pasa de estado pendiente a enviado y el mecanismo de despacho lo procesa.
- Al cancelar, queda en estado cancelado ([RN-17](05_reglas_de_negocio.md#rn-17)).

→ Ref: [F3.3](06_funcionalidades.md#f33--aprobación-de-envíos-masivos), [PA-03](10_preguntas_abiertas.md#pa-03)

---

### HU-13 🟡 ✅ — Recibir y responder mensajes internos
**Como** DOCENTE (PROFESOR o COORDINADOR)
**Quiero** ver mi bandeja de entrada y responder mensajes internos desde mi perfil
**Para** mantener comunicación interna con coordinación y el sistema.

**CA**:
- Desde mi perfil accedo a los hilos de conversación activos.
- Puedo responder indicando asunto y cuerpo.
- La respuesta queda asociada al hilo original.

→ Ref: [F3.4](06_funcionalidades.md#f34--mensajería-interna-inbox-del-docente)

---

### HU-14 🟡 ✅ — Publicar aviso del sistema con alcance y vigencia
**Como** COORDINADOR
**Quiero** publicar avisos segmentados por materia, cohorte y rol, con una ventana de vigencia
**Para** comunicar novedades a los docentes pertinentes sin impactar al resto.

**CA**:
- Defino el alcance: global, por materia, por cohorte; el rol destino; y la severidad del aviso.
- Defino fecha y hora de inicio y de fin — el aviso solo se muestra dentro de esa ventana ([RN-18](05_reglas_de_negocio.md#rn-18)).
- Puedo requerir acuse de recibo obligatorio (`require_ack`) ([RN-19](05_reglas_de_negocio.md#rn-19)).
- El listado muestra contadores de vistos y de acuses recibidos.

→ Ref: [F3.5](06_funcionalidades.md#f35--avisos-del-sistema-tablón)

---

### HU-15 🟢 ✅ — Acusar recibo de un aviso obligatorio
**Como** DOCENTE
**Quiero** confirmar que leí un aviso marcado con acuse obligatorio
**Para** dejar registro de cumplimiento ante la institución.

**CA**:
- El sistema registra mi confirmación en el contador agregado del aviso.
- Una vez confirmado, el aviso queda marcado como leído para mí.

→ Ref: [RN-19](05_reglas_de_negocio.md#rn-19)

---

## Épica 4 — Gestión de Equipos Docentes

### HU-16 🔴 ✅ — Dar de alta un usuario docente
**Como** COORDINADOR o ADMIN
**Quiero** registrar un nuevo usuario con sus datos personales y bancarios
**Para** que pueda recibir asignaciones y liquidaciones.

**CA**:
- Datos requeridos: nombre completo, DNI, banco, CBU, alias CBU, regional, email institucional.
- Datos opcionales: identificador profesional (por ejemplo, matrícula), documentación adicional.
- El sistema asigna un identificador interno único (no editable) al crear el usuario.
- El estado inicial puede ser activo o inactivo.
- Los roles se asignan desde el módulo de permisos, no como un flag binario ([03 — Actores y Roles](03_actores_y_roles.md)).

→ Ref: [F4.1](06_funcionalidades.md#f41--abm-de-usuarios-docentes)

---

### HU-17 🟡 ✅ — Ver mis equipos de trabajo
**Como** DOCENTE
**Quiero** ver en qué materias, carrera, cohorte y rol estoy asignado actualmente
**Para** tener una vista consolidada de mis responsabilidades.

**CA**:
- La tabla muestra Carrera | Cohorte | Rol | Comisiones | Vigencia | Estado.
- El estado (vigente / vencido) se deriva del rango de fechas de la asignación ([RN-10](05_reglas_de_negocio.md#rn-10)).
- Puedo filtrar por estado, materia, rol, carrera y cohorte.

→ Ref: [F4.2](06_funcionalidades.md#f42--mis-equipos-vista-propia)

---

### HU-18 🔴 ✅ — Asignar masivamente docentes a una materia
**Como** COORDINADOR
**Quiero** asignar múltiples docentes a una materia × carrera × cohorte × rol en una sola operación
**Para** acelerar el setup de inicio de cuatrimestre.

**CA**:
- Selecciono materia, carrera, cohorte, rol, fechas de vigencia y comisiones.
- Puedo seleccionar múltiples docentes con checkboxes o mediante búsqueda en volumen ([RN-30](05_reglas_de_negocio.md#rn-30)).
- Puedo indicar uno o varios responsables jerárquicos (quién coordina a quién dentro del equipo) ([RN-11](05_reglas_de_negocio.md#rn-11)).

→ Ref: [F4.4](06_funcionalidades.md#f44--asignación-masiva)

---

### HU-19 🔴 ✅ — Clonar equipo docente entre cohortes
**Como** COORDINADOR
**Quiero** copiar todas las asignaciones de una materia/carrera/cohorte origen a otra cohorte destino
**Para** no recrear manualmente el equipo al cambiar de cuatrimestre.

**CA**:
- Defino el origen (materia × carrera × cohorte) y el destino (ídem).
- El sistema duplica las asignaciones con las fechas correspondientes al destino ([RN-12](05_reglas_de_negocio.md#rn-12)).
- Se confirma la operación con un resumen o mensaje de éxito.

→ Ref: [F4.5](06_funcionalidades.md#f45--clonar-equipo-docente)

---

### HU-20 🟡 ✅ — Modificar vigencia general de un equipo
**Como** COORDINADOR
**Quiero** cambiar las fechas de vigencia de todas las asignaciones de un equipo en bloque
**Para** ajustar el período cuando cambia el calendario académico.

**CA**:
- Selecciono el equipo (materia × carrera × cohorte).
- Defino las nuevas fechas de inicio y fin de vigencia.
- El cambio se aplica a todas las asignaciones vigentes del equipo.

→ Ref: [F4.6](06_funcionalidades.md#f46--modificar-vigencia-general-del-equipo)

---

## Épica 5 — Estructura Académica

### HU-21 🟡 ✅ — Administrar carreras
**Como** COORDINADOR o ADMIN
**Quiero** crear, editar y desactivar carreras (código + nombre)
**Para** mantener actualizado el catálogo institucional.

**CA**:
- Campos requeridos: código único (ej. "TUPAD") y nombre completo.
- Estados posibles: Activa / Inactiva.
- No se puede eliminar una carrera con cohortes o asignaciones asociadas; solo desactivar.

→ Ref: [F5.1](06_funcionalidades.md#f51--abm-de-carreras)

---

### HU-22 🔴 ✅ — Administrar cohortes
**Como** COORDINADOR o ADMIN
**Quiero** crear cohortes con nombre, año, fecha de inicio y fecha de fin
**Para** que las asignaciones y avisos puedan asociarse a períodos específicos.

**CA**:
- Campos requeridos: nombre (ej. "MAR-2026"), año, fecha de inicio.
- La fecha de fin es opcional (cohorte abierta).
- Se puede desactivar una cohorte sin perder el histórico.

→ Ref: [F5.2](06_funcionalidades.md#f52--abm-de-cohortes)

---

### HU-23 🟡 ✅ — Subir programa de materia
**Como** COORDINADOR
**Quiero** subir el programa de cada materia por carrera y cohorte
**Para** que los docentes y la institución tengan la versión oficial centralizada.

**CA**:
- Selecciono materia + carrera + cohorte + título + archivo (formato PDF).
- Puedo listar, descargar y reemplazar programas existentes.
- La vista es filtrable por materia, carrera y cohorte.

→ Ref: [F5.3](06_funcionalidades.md#f53--programas-de-materias)

---

### HU-24 🟡 ✅ — Gestionar fechas de evaluaciones
**Como** COORDINADOR
**Quiero** cargar las fechas clave de evaluación (parciales, TPs, coloquios) por materia y cohorte
**Para** que los docentes y alumnos sepan cuándo es cada instancia.

**CA**:
- Campos: materia, tipo de evaluación (Parcial / TP / Coloquio), número de instancia, fecha, cohorte, título.
- Vistas disponibles: tabla lineal y calendario de evaluaciones.
- Existe una función para generar el cronograma en formato embebible en el LMS.

→ Ref: [F5.4](06_funcionalidades.md#f54--fechas-de-evaluaciones)

---

## Épica 6 — Encuentros y Disponibilidad

### HU-25 🔴 ✅ — Crear slot de encuentro recurrente
**Como** PROFESOR
**Quiero** definir un encuentro recurrente (mismo día y hora durante N semanas)
**Para** que el sistema genere automáticamente todas las instancias del cuatrimestre.

**CA**:
- Modo recurrente: día de la semana + hora + fecha de inicio + cantidad de semanas ([RN-13](05_reglas_de_negocio.md#rn-13)).
- Se generan N instancias automáticamente.
- Cada instancia hereda materia, título y enlace de videoconferencia.

→ Ref: [F6.1](06_funcionalidades.md#f61--crear-slot-de-encuentro-recurrente)

---

### HU-26 🟡 ✅ — Crear encuentro único (no recurrente)
**Como** PROFESOR
**Quiero** crear un encuentro de una sola fecha
**Para** los casos especiales (recuperatorios, charlas, eventos puntuales).

**CA**:
- Modo único: una sola fecha + hora + título + enlace de videoconferencia.

→ Ref: [F6.2](06_funcionalidades.md#f62--crear-encuentro-único)

---

### HU-27 🟡 ✅ — Editar instancia individual de encuentro
**Como** PROFESOR
**Quiero** editar el estado, enlace de videoconferencia, enlace de grabación y comentarios de cada instancia
**Para** llevar registro de lo que efectivamente ocurrió ([RN-14](05_reglas_de_negocio.md#rn-14)).

**CA**:
- Edito la instancia individualmente, sin afectar el slot recurrente original.
- El campo de enlace de grabación queda disponible para completar post-encuentro.

→ Ref: [F6.3](06_funcionalidades.md#f63--editar-instancia-de-encuentro)

---

### HU-28 🟢 ✅ — Generar cronograma de encuentros embebible en el LMS
**Como** PROFESOR
**Quiero** obtener un fragmento de contenido con mis slots/instancias
**Para** pegarlo en el aula virtual sin formatearlo manualmente.

**CA**:
- El sistema genera un fragmento en el formato adecuado para el LMS, listo para copiar y pegar.

→ Ref: [F6.4](06_funcionalidades.md#f64--generar-cronograma-embebible)

---

### HU-29 🟡 ✅ — Ver mis guardias realizadas
**Como** TUTOR o PROFESOR
**Quiero** ver el historial de mis guardias con día, horario, estado y comentarios
**Para** llevar registro de mi disponibilidad efectiva.

**CA**:
- Tabla con: responsable | materia | carrera/cohorte | día | horario | estado | comentarios | fecha de registro.
- Estado mínimo esperado: "finalizado".
- Puedo exportar el historial.
- (→ [PA-05](10_preguntas_abiertas.md#pa-05): el flujo de alta de guardia está pendiente de detalle.)

→ Ref: [F6.6](06_funcionalidades.md#f66--registro-de-guardias)

---

## Épica 7 — Coloquios

### HU-30 🟡 ✅ — Importar alumnos para una instancia de coloquio
**Como** PROFESOR
**Quiero** cargar el padrón de alumnos elegibles para una instancia de coloquio
**Para** convocar solo a quienes corresponde.

**CA**:
- Existe un flujo dedicado para la importación del padrón de coloquio, separado del padrón general.

→ Ref: [F7.2](06_funcionalidades.md#f72--importar-alumnos-a-coloquios)

---

### HU-31 🔴 ✅ — Crear nueva convocatoria de coloquio
**Como** PROFESOR
**Quiero** definir una evaluación de coloquio con materia, instancia, días disponibles y cupos
**Para** que los alumnos puedan reservar lugar.

**CA**:
- Se completan los datos de la convocatoria (materia, instancia, días, cupos por franja).
- El listado posterior muestra Convocados, Reservas activas y Cupos disponibles.

→ Ref: [F7.3](06_funcionalidades.md#f73--nueva-convocatoria-de-coloquio)

---

### HU-32 🟡 ✅ — Ver agenda consolidada de reservas
**Como** COORDINADOR
**Quiero** ver todas las reservas activas de coloquios en una agenda
**Para** anticipar carga operativa y solapamientos.

**CA**:
- Vista de agenda con filtros: materia, responsable, rango de fechas y búsqueda libre.

→ Ref: [F7.5](06_funcionalidades.md#f75--administración-de-coloquios)

---

### HU-33 🟡 ✅ — Ver registro académico consolidado de coloquios
**Como** COORDINADOR
**Quiero** ver las notas finales consolidadas de los coloquios rendidos
**Para** auditar resultados y generar reportes oficiales.

**CA**:
- Vista de registro académico con las notas finales de todas las instancias de coloquio.

→ Ref: [F7.5](06_funcionalidades.md#f75--administración-de-coloquios)

---

## Épica 8 — Workflow de Tareas

### HU-34 🟡 ✅ — Ver mis tareas asignadas
**Como** PROFESOR
**Quiero** ver las tareas que la coordinación me asignó
**Para** organizar mi trabajo administrativo.

**CA**:
- Listado filtrable por contexto (materia, estado).
- Veo descripción, último comentario y estado de cada tarea.

→ Ref: [F8.1](06_funcionalidades.md#f81--mis-tareas-vista-profesor)

---

### HU-35 🟡 ✅ — Delegar una tarea a otro docente
**Como** PROFESOR
**Quiero** asignar una tarea a un colega
**Para** delegar trabajo de coordinación interna entre el equipo.

**CA**:
- Desde la vista de mis tareas puedo reasignar una tarea a otro docente del tenant.

→ Ref: [F8.2](06_funcionalidades.md#f82--asignar-tarea-entre-docentes)

---

### HU-36 🔴 ✅ — Administrar todas las tareas (coordinación)
**Como** COORDINADOR
**Quiero** ver, filtrar y actualizar el estado de todas las tareas del sistema
**Para** dar seguimiento al workflow del equipo docente.

**CA**:
- Listado con filtros por docente asignado, asignador, materia, estado y búsqueda libre.
- Puedo cambiar el estado y agregar un comentario en cada tarea.
- (→ [PA-08](10_preguntas_abiertas.md#pa-08): el ciclo de vida completo del estado de tarea está pendiente de documentar.)

→ Ref: [F8.3](06_funcionalidades.md#f83--administrar-tareas-coordinación)

---

## Épica 9 — Auditoría y Métricas

### HU-37 🔴 ✅ — Ver panel de interacciones por docente
**Como** COORDINADOR
**Quiero** ver acciones por período, estado de comunicaciones y métricas por docente × materia
**Para** identificar docentes inactivos o con problemas operativos.

**CA**:
- Filtros: rango de fechas, materia, docente, "inactivos".
- Tablas: estado de comunicaciones (pendiente / enviado / OK / fallido / cancelado) e interacciones por docente y materia (previsualización, importación, envío, reset, umbral, envíos exitosos, fallidos, batches).
- Última actividad por docente visible.

→ Ref: [F9.1](06_funcionalidades.md#f91--panel-de-interacciones)

---

### HU-38 🔴 ✅ — Auditar acciones individuales
**Como** COORDINADOR o ADMIN
**Quiero** ver el registro de las últimas acciones con timestamp, usuario, materia, código de acción, registros afectados, IP de origen y agente de usuario
**Para** investigar incidentes y mantener trazabilidad regulatoria.

**CA**:
- El registro de auditoría muestra las acciones más recientes (con un límite configurable) ([RN-23](05_reglas_de_negocio.md#rn-23)).
- Cada entrada incluye un código semántico de acción (ej. `ASIGNACION_EQUIPO`).

→ Ref: [F9.2](06_funcionalidades.md#f92--log-de-auditoría-completo)

---

## Épica 10 — Liquidaciones y Honorarios

### HU-39 🔴 ✅ — Ver vista previa de liquidación del período
**Como** FINANZAS
**Quiero** ver la liquidación calculada por docente con Base + Plus + Total
**Para** validar antes de cerrar el período ([RN-21](05_reglas_de_negocio.md#rn-21)).

**CA**:
- Tabla con columnas: Docente | Rol | Comisiones | Base | Plus | Total.
- Puedo ver la previsualización antes de confirmar el cierre.
- Puedo exportar la previsualización sin cerrar el período.

→ Ref: [F10.1](06_funcionalidades.md#f101--vista-de-liquidaciones)

---

### HU-40 🔴 ✅ — Cerrar liquidación de un período
**Como** FINANZAS
**Quiero** cerrar la liquidación calculada
**Para** inmutabilizar los montos del período y proceder al pago ([RN-22](05_reglas_de_negocio.md#rn-22)).

**CA**:
- La acción de cierre requiere confirmación explícita.
- Una vez cerrada, la liquidación no puede modificarse.
- Queda disponible en el historial para auditoría posterior.

→ Ref: [F10.2](06_funcionalidades.md#f102--cerrar-liquidación)

---

### HU-41 🟡 ✅ — Mantener la grilla de salarios
**Como** FINANZAS
**Quiero** mantener la grilla maestra de salarios (por rol y posibles dimensiones adicionales)
**Para** que el cálculo automático del salario base sea consistente ([S5](09_decisiones_y_supuestos.md#s5)).

**CA**:
- El acceso está restringido al permiso `liquidaciones:administrar-grilla`.
- (→ [PA-06](10_preguntas_abiertas.md#pa-06): la fórmula exacta de cálculo está pendiente de documentar.)

→ Ref: [F10.4](06_funcionalidades.md#f104--abm-de-grilla-salarial)

---

## Épica 11 — Perfil y Sesión

### HU-42 🟡 ✅ — Editar mis datos personales y bancarios
**Como** DOCENTE
**Quiero** actualizar mis datos personales y bancarios desde mi perfil
**Para** que las liquidaciones lleguen a la cuenta correcta y mis datos estén al día.

**CA**:
- Campos editables: nombre completo, DNI, género, banco, CBU, alias CBU, regional, email, condición frente al impuesto (monotributista o no), identificador profesional opcional.
- El CUIL es de solo lectura (lo gestiona el ADMIN del tenant) ([S6](09_decisiones_y_supuestos.md#s6)).

→ Ref: [F11.1](06_funcionalidades.md#f111--editar-perfil)

---

### HU-43 🟢 ✅ — Cerrar sesión
**Como** cualquier USUARIO autenticado
**Quiero** cerrar mi sesión desde el menú
**Para** proteger mi acceso cuando termino de trabajar.

**CA**:
- La acción de cierre de sesión revoca el token de refresco del lado del servidor.
- El token de acceso activo se descarta en el cliente.
- El usuario es redirigido a la pantalla de inicio de sesión.
- La acción queda registrada en la auditoría.

→ Ref: [F11.3](06_funcionalidades.md#f113--logout), [`ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md)

---

## Épica 12 — Integraciones con Servicios Externos

### HU-44 🟢 ✅ — Acceder a un servicio externo de corrección asistida
**Como** PROFESOR
**Quiero** acceder desde el sistema a un servicio externo de corrección asistida por IA
**Para** apoyarme en correcciones automatizadas.

**CA**:
- El sistema provee un punto de acceso (enlace o integración) al servicio externo configurado para el tenant.
- El comportamiento del servicio externo no es responsabilidad de este sistema.
- La URL del servicio es configurable por tenant (no está hardcodeada).

→ Ref: [F12.1](06_funcionalidades.md#f121--integración-con-servicio-externo-de-corrección)

---

## Épica 13 — Facturación de Monotributistas

### HU-48 🔴 ✅ — Gestionar facturas de docentes monotributistas
**Como** FINANZAS
**Quiero** ver, filtrar y marcar como abonadas las facturas que presentan los docentes monotributistas
**Para** llevar control del pago paralelo a la liquidación general.

**CA**:
- Listado con filtros: docente, estado (pendiente / abonada), rango de fechas, búsqueda libre.
- Cada factura muestra: fecha de carga, docente, período (AAAA-MM), detalle en texto libre, archivo adjunto descargable, tamaño, estado y fecha de pago.
- Estados: pendiente ([RN-39](05_reglas_de_negocio.md#rn-39)) → abonada.
- El cambio de estado requiere confirmación explícita.

→ Ref: [F10.5](06_funcionalidades.md#f105--gestión-de-facturas-monotributistas)

---

### HU-49 ❓ — Docente sube su factura mensual
**Como** PROFESOR monotributista
**Quiero** subir mi factura mensual en formato PDF
**Para** que la administración la procese.

**CA pendientes** (→ [PA-06](10_preguntas_abiertas.md#pa-06)):
- ¿Desde qué pantalla del perfil o panel docente se accede al formulario de carga?
- ¿Hay validación del monto contra la liquidación calculada equivalente?
- ¿Se genera una notificación al área de Finanzas cuando hay una nueva factura cargada?

---

## Historias pendientes de detalle

### HU-45 ✅ — Iniciar sesión en la plataforma
**Como** USUARIO con credenciales válidas
**Quiero** iniciar sesión en la plataforma
**Para** acceder a las funcionalidades correspondientes a mi rol.

**CA**:
- El identificador de acceso es el email institucional (nunca un número de legajo ni otro identificador numérico).
- La contraseña se valida de forma segura; la política de almacenamiento es responsabilidad de la arquitectura (ver [`ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md)).
- El segundo factor (2FA tipo TOTP) es opcional para el usuario; puede habilitarlo desde su perfil.
- La recuperación de contraseña se realiza por email con un token de un solo uso y tiempo de expiración.
- No existe auto-registro: el alta de usuarios es siempre administrativa.
- La identidad y el tenant del usuario se derivan exclusivamente de la sesión autenticada; ningún parámetro de la petición puede modificarlos ([03 — Actores y Roles](03_actores_y_roles.md)).

→ Ref: [F11.2](06_funcionalidades.md#f112--autenticación-y-sesión), [`ARQUITECTURA.md` §5](../docs/ARQUITECTURA.md)

---

### HU-46 ❓ — Registrar una guardia
**Como** TUTOR o PROFESOR
**Quiero** registrar una nueva guardia
**Para** que quede en mi historial de disponibilidad.

**CA pendientes** (→ [PA-05](10_preguntas_abiertas.md#pa-05)):
- ¿Desde qué pantalla o flujo se inicia el alta de una guardia?
- ¿Es un subflujo de encuentros, de tareas, o un módulo independiente?

---

### HU-47 ❓ — Alumno reserva una instancia de coloquio
**Como** ALUMNO
**Quiero** reservar un lugar en una instancia de coloquio disponible
**Para** rendir según mi disponibilidad.

**CA pendientes** (→ [PA-14](10_preguntas_abiertas.md#pa-14)):
- ¿La reserva ocurre dentro de este sistema o en el LMS?
- ¿Existe una interfaz dedicada para el rol ALUMNO?

---

## Resumen por épica

| Épica | HUs | ✅ Definidas | ❓ Pendientes de detalle |
|-------|-----|-------------|--------------------------|
| 1 — Ingesta LMS | HU-01..04 | 4 | 0 |
| 2 — Análisis | HU-05..09 | 5 | 0 |
| 3 — Comunicación | HU-10..15 | 5 | 1 |
| 4 — Equipos | HU-16..20 | 5 | 0 |
| 5 — Estructura | HU-21..24 | 4 | 0 |
| 6 — Encuentros | HU-25..29 | 5 | 0 |
| 7 — Coloquios | HU-30..33 | 4 | 0 |
| 8 — Tareas | HU-34..36 | 3 | 0 |
| 9 — Auditoría | HU-37..38 | 2 | 0 |
| 10 — Liquidaciones | HU-39..41 | 3 | 0 |
| 11 — Perfil y Sesión | HU-42..43, HU-45 | 3 | 0 |
| 12 — Integraciones externas | HU-44 | 1 | 0 |
| 13 — Facturación monotributistas | HU-48..49 | 1 | 1 |
| Pendientes de detalle | HU-46..47 | — | 2 |
| **TOTAL** | **49 HU** | **45** | **4** |

---

## Convenciones para futuras HUs

Si surgen nuevas historias de usuario:
- Continuar la numeración desde HU-50 en adelante.
- Vincular siempre a una épica de [06 — Funcionalidades](06_funcionalidades.md) y a las reglas de negocio aplicables de [05 — Reglas de Negocio](05_reglas_de_negocio.md).
- Marcar estado: ✅ / 🔧 / ❓.
- Si la HU implica una nueva regla de negocio, agregarla a [05 — Reglas de Negocio](05_reglas_de_negocio.md) y referenciarla desde la CA.
