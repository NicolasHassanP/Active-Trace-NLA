# 06 — Funcionalidades

> **Propósito**: catálogo de funcionalidades del sistema agrupadas por **épica**, expresado en lenguaje de dominio y agnóstico de tecnología. Describe QUÉ hace el sistema y qué valor aporta a cada actor, sin referir a pantallas, rutas ni stacks de ninguna implementación concreta. El CÓMO se construye cada capacidad vive en [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md). Los roles y permisos referenciados están definidos en [`03_actores_y_roles.md`](03_actores_y_roles.md). Las reglas de negocio se detallan en [`05_reglas_de_negocio.md`](05_reglas_de_negocio.md).

---

## Épica 1 — Ingesta de Datos desde el LMS

### F1.1 — Importar calificaciones por materia

- **Quién**: PROFESOR (sobre sus propias materias); COORDINADOR (sobre cualquier materia del tenant)
- **Flujo**:
  1. El usuario selecciona la materia destino.
  2. Sube el archivo de calificaciones exportado desde el LMS (formato hoja de cálculo estándar).
  3. El sistema genera una vista previa de las actividades y alumnos detectados.
  4. El usuario selecciona qué actividades incluir en el análisis.
- **Valor**: permite al docente trabajar con datos reales del LMS sin necesidad de acceso directo a la plataforma educativa.
- **Reglas aplicadas**: [RN-01](05_reglas_de_negocio.md#rn-01), [RN-02](05_reglas_de_negocio.md#rn-02)

### F1.2 — Importar reporte de finalización de actividades

- **Quién**: PROFESOR; COORDINADOR
- **Propósito**: detectar trabajos prácticos entregados pero aún sin calificación registrada.
- **Entrada aceptada**: archivo exportado desde el LMS con el estado de finalización de actividades por alumno (formatos de hoja de cálculo o texto delimitado).
- **Salida**: listado de actividades potencialmente sin corregir, identificadas por alumno y actividad.
- **Reglas aplicadas**: [RN-07](05_reglas_de_negocio.md#rn-07), [RN-08](05_reglas_de_negocio.md#rn-08)

### F1.3 — Importar padrón de alumnos

- **Quién**: PROFESOR (para sus materias); COORDINADOR (global)
- **Datos importados**: nombre, apellido(s), dirección de correo, grupos/comisiones.
- **Comportamiento**: upsert destructivo — el padrón anterior de la materia queda reemplazado por el importado ([RN-05](05_reglas_de_negocio.md#rn-05)).

### F1.4 — Importar listado de participantes y actividades (coordinación)

- **Quién**: COORDINADOR
- **Flujo en dos pasos**:
  1. Importar el listado de participantes (padrón general).
  2. Importar el detalle de actividades y calificaciones asociadas.
- **Valor**: permite a coordinación consolidar datos de múltiples materias en una sola operación supervisada.

### F1.5 — Vaciar datos de una materia

- **Quién**: PROFESOR (solo sus propios datos); COORDINADOR
- **Efecto**: elimina todos los datos de calificaciones e ingesta importados para la materia seleccionada, sin afectar otras materias ni datos de otros docentes.
- **Reglas aplicadas**: [RN-04](05_reglas_de_negocio.md#rn-04)

---

## Épica 2 — Análisis y Reportes Académicos

### F2.1 — Configurar umbral de aprobación por materia

- **Quién**: PROFESOR
- **Descripción**: el docente define el porcentaje mínimo de nota que considera aprobatorio para su materia. Valor por defecto: 60%.
- **Efecto**: afecta todos los cálculos de "atrasados" y "ranking" de esa materia.
- **Reglas aplicadas**: [RN-03](05_reglas_de_negocio.md#rn-03)

### F2.2 — Visualizar alumnos atrasados

- **Quién**: TUTOR, PROFESOR, COORDINADOR, ADMIN
- **Definición de "atrasado"**: alumno con actividades faltantes o con nota inferior al umbral configurado en la materia.
- **Valor**: facilita la detección temprana de alumnos en riesgo académico para activar el acompañamiento.
- **Reglas aplicadas**: [RN-06](05_reglas_de_negocio.md#rn-06)

### F2.3 — Ranking de actividades aprobadas

- **Quién**: PROFESOR, COORDINADOR
- **Salida**: tabla ordenada por cantidad de actividades aprobadas por alumno.
- **Filtro implícito**: solo incluye alumnos con al menos una actividad aprobada.
- **Reglas aplicadas**: [RN-09](05_reglas_de_negocio.md#rn-09)

### F2.4 — Reportes rápidos por materia

- **Quién**: PROFESOR, COORDINADOR
- **Descripción**: vista consolidada con métricas clave de la materia a partir de los datos importados (actividades, aprobaciones, tendencias). Muestra un estado informativo cuando aún no hay datos o no se seleccionaron actividades.

### F2.5 — Notas finales agrupadas

- **Quién**: PROFESOR
- **Descripción**: el sistema agrupa las actividades configuradas y calcula una nota final por alumno, lista para exportar o registrar formalmente.
- **Valor**: simplifica la confección de actas o informes de cierre de período.

### F2.6 — Exportar trabajos prácticos sin corregir

- **Quién**: PROFESOR, COORDINADOR
- **Salida**: archivo descargable con el listado de entregas detectadas como pendientes de corrección.
- **Valor**: permite gestionar la cola de correcciones fuera del sistema.

### F2.7 — Monitor general de actividades (coordinación y administración)

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: vista transversal de todos los alumnos del tenant con su estado de actividades.
- **Filtros disponibles**: materia, regional, comisión, búsqueda libre por alumno, estado de actividad, criterio de clasificación.
- **Acciones**: aplicar filtros, exportar, limpiar selección.

### F2.8 — Monitor de seguimiento de alumnos (vista tutor/profesor)

- **Quién**: TUTOR, PROFESOR
- **Descripción**: vista filtrable del estado de actividades de los alumnos asignados al usuario, con posibilidad de acotar por alumno, correo, comisión, regional, actividad y mínimo de actividad cumplida.

### F2.9 — Monitor de seguimiento de alumnos (vista coordinación/admin)

- **Quién**: COORDINADOR, ADMIN
- **Extiende a**: [F2.8](#f28--monitor-de-seguimiento-de-alumnos-vista-tutorprofesor)
- **Filtros adicionales**: rango de fechas para acotar el período de análisis.

---

## Épica 3 — Comunicación con Alumnos

### F3.1 — Vista previa de comunicaciones

- **Quién**: todo rol con permiso `comunicacion:enviar`
- **Descripción**: antes de enviar cualquier mensaje, el sistema presenta una previsualización del asunto y del cuerpo del mensaje tal como lo recibirá el destinatario.
- **Valor**: reduce errores de contenido en envíos masivos.
- **Reglas aplicadas**: [RN-16](05_reglas_de_negocio.md#rn-16)

### F3.2 — Envío masivo de comunicaciones con cola

- **Quién**: PROFESOR (sus propias comisiones); COORDINADOR; ADMIN
- **Estados del mensaje en cola**: Pendiente → En envío → Enviado / Fallido / Cancelado.
- **Tracking**: el estado de cada envío es visible en tiempo real en el panel de comunicaciones.
- **Reglas aplicadas**: [RN-15](05_reglas_de_negocio.md#rn-15)

### F3.3 — Aprobación de envíos masivos

- **Quién**: rol con permiso `comunicacion:aprobar` (típicamente COORDINADOR o ADMIN)
- **Descripción**: los envíos masivos que superen cierto volumen o impacto pasan por una cola de aprobación antes de ejecutarse. Un aprobador revisa el contenido y habilita o rechaza el envío.
- **Valor**: control de calidad y prevención de comunicaciones erróneas a escala.
- **Reglas aplicadas**: [RN-17](05_reglas_de_negocio.md#rn-17)

### F3.4 — Mensajería interna (bandeja del docente)

- **Quién**: TUTOR, PROFESOR, COORDINADOR, ADMIN
- **Capacidades**: leer hilos de mensajes recibidos, responder a un mensaje dentro del hilo.
- **Uso**: la bandeja recibe notificaciones del sistema, avisos de coordinación y respuestas de otros actores.

### F3.5 — Tablón de avisos del sistema

- **Quién lectura**: todos los roles (según scope del aviso). **Quién gestión**: COORDINADOR, ADMIN.
- **Capacidades de gestión**: alta, baja y modificación de avisos; configuración de alcance (global / por materia / por cohorte), severidad, rol(es) destinatario(s), vigencia (fecha inicio y fin), ordenamiento y requerimiento de confirmación de lectura (*acknowledgment*).
- **Reglas aplicadas**: [RN-18](05_reglas_de_negocio.md#rn-18), [RN-19](05_reglas_de_negocio.md#rn-19), [RN-20](05_reglas_de_negocio.md#rn-20)

---

## Épica 4 — Gestión de Equipos Docentes

### F4.1 — Administración de usuarios del equipo docente

- **Quién**: ADMIN
- **Capacidades**: alta, edición y activación/desactivación de usuarios con rol docente (PROFESOR, TUTOR, NEXO, COORDINADOR).
- **Datos gestionados**: nombre, identificación fiscal, datos bancarios para liquidación (banco, CBU / alias), regional, estado de actividad, rol, información de facturación.
- **Nota**: el modelo de permisos finos reemplaza cualquier flag binario de "administrador". Ver [`03_actores_y_roles.md`](03_actores_y_roles.md).

### F4.2 — Vista de mis equipos (propia del docente)

- **Quién**: PROFESOR, TUTOR, NEXO, COORDINADOR
- **Descripción**: el usuario ve las comisiones y materias en las que está asignado, con el rol que ejerce, la carrera, la cohorte, las comisiones asociadas, la vigencia de la asignación y su estado.
- **Vistas disponibles**: resumen del equipo, monitoreo de actividad, vista de comunicaciones del equipo.
- **Filtros**: estado, materia, rol, carrera, cohorte.

### F4.3 — Consulta y gestión de asignaciones individuales

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: vista de todas las asignaciones activas del tenant, con filtros por materia, carrera, cohorte, identificador de usuario, nombre de docente, rol y relación de reporte.

### F4.4 — Asignación masiva de docentes

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: permite seleccionar múltiples docentes y asignarlos en bloque a una combinación materia × carrera × cohorte × rol, con una vigencia definida.
- **Valor**: agiliza la configuración del equipo al inicio de cada período académico.
- **Reglas aplicadas**: [RN-30](05_reglas_de_negocio.md#rn-30)

### F4.5 — Clonar equipo docente entre períodos

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: duplica todas las asignaciones de un equipo origen (materia × carrera × cohorte) hacia un destino, facilitando la migración entre cuatrimestres sin tener que reconfigurar todo desde cero.
- **Reglas aplicadas**: [RN-12](05_reglas_de_negocio.md#rn-12)

### F4.6 — Modificar vigencia general del equipo

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: actualiza las fechas de vigencia (desde / hasta) de todas las asignaciones pertenecientes a un equipo seleccionado en una sola operación.

### F4.7 — Exportar equipo docente

- **Quién**: COORDINADOR, ADMIN
- **Salida**: archivo descargable con el detalle de todas las asignaciones del equipo (docente, rol, materia, carrera, cohorte, vigencia, estado).

---

## Épica 5 — Estructura Académica

### F5.1 — Administración de carreras

- **Quién**: ADMIN
- **Capacidades**: alta, edición y cambio de estado (activa / inactiva) de carreras.
- **Datos**: código identificador y nombre descriptivo de la carrera.

### F5.2 — Administración de cohortes

- **Quién**: ADMIN
- **Capacidades**: alta, edición y cambio de estado de cohortes.
- **Datos**: nombre, año de inicio, fechas de vigencia (desde / hasta), estado.
- **Ejemplos de nomenclatura**: MAR-2025, AGO-2025, MAR-2026.

### F5.3 — Gestión de programas de materias

- **Quién**: ADMIN, COORDINADOR
- **Capacidades**: subir y asociar el programa oficial (en formato documento) de cada materia para una combinación específica de carrera × cohorte, con un título descriptivo.
- **Valor**: centraliza los programas vigentes y los hace accesibles a los actores autorizados.

### F5.4 — Gestión de fechas de evaluaciones

- **Quién**: COORDINADOR, ADMIN
- **Capacidades**: registrar y editar las fechas de parciales, trabajos prácticos y coloquios por materia, cohorte y número de instancia.
- **Datos**: materia, tipo de evaluación (parcial / TP / coloquio), número de instancia, fecha, cohorte, título descriptivo.
- **Vistas disponibles**: listado tabular y calendario visual de evaluaciones.
- **Salida adicional**: el sistema puede generar un fragmento de contenido listo para publicar en el aula virtual del LMS.

---

## Épica 6 — Encuentros y Disponibilidad

### F6.1 — Crear encuentro recurrente

- **Quién**: PROFESOR, COORDINADOR
- **Descripción**: el docente define un slot de encuentro que se repite con periodicidad semanal durante un número determinado de semanas. El sistema genera automáticamente todas las instancias.
- **Datos de configuración**: materia, horario, día de la semana, fecha de inicio, cantidad de semanas, título, enlace de videoconferencia.

### F6.2 — Crear encuentro único

- **Quién**: PROFESOR, COORDINADOR
- **Descripción**: creación de una instancia de encuentro para una fecha y hora específicas, sin recurrencia.
- **Datos**: fecha, horario, título, enlace de videoconferencia.

### F6.3 — Editar instancia de encuentro

- **Quién**: PROFESOR, COORDINADOR
- **Campos modificables**: estado del encuentro, enlace de videoconferencia, enlace de grabación (disponible después de realizado el encuentro), comentario interno.

### F6.4 — Generar contenido para el aula virtual

- **Quién**: PROFESOR, COORDINADOR
- **Salida**: fragmento de contenido formateado con los encuentros programados, listo para publicar en el aula virtual del LMS.

### F6.5 — Vista de encuentros (coordinación/admin)

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: vista transversal de todos los encuentros del tenant, más allá del docente que los creó. Permite supervisión y monitoreo global.

### F6.6 — Registro de guardias

- **Quién**: TUTOR (registro propio); COORDINADOR, ADMIN (consulta global)
- **Descripción**: registro de las guardias cubiertas por tutores, con datos de quién cubrió, la materia, la carrera/cohorte, el día, el horario, el estado y los comentarios asociados.
- **Acciones**: consulta filtrada y exportación del registro.

---

## Épica 7 — Coloquios

### F7.1 — Panel de métricas de coloquios

- **Quién**: COORDINADOR, ADMIN
- **Métricas expuestas**: total de alumnos cargados, cantidad de instancias activas, reservas activas, notas registradas.
- **Valor**: estado de situación de las evaluaciones orales de un vistazo.

### F7.2 — Importar alumnos a una convocatoria de coloquio

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: carga o actualiza el padrón de alumnos habilitados para una convocatoria específica de coloquio.

### F7.3 — Crear convocatoria de coloquio

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: el usuario crea una nueva convocatoria de evaluación oral (coloquio), definiendo la materia, la instancia y los días y cupos disponibles.

### F7.4 — Listado de convocatorias

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: vista tabular de todas las convocatorias activas con sus métricas operativas (materia, instancia, días disponibles, convocados, reservas activas, cupos libres) y acciones de gestión.

### F7.5 — Administración global de coloquios

- **Quién**: ADMIN
- **Sub-secciones**:
  - Gestión de convocatorias (alta, edición, cierre).
  - Registro académico consolidado de resultados.
  - Agenda de reservas activas por convocatoria.

---

## Épica 8 — Workflow de Tareas Internas

### F8.1 — Vista de mis tareas (docente)

- **Quién**: TUTOR, PROFESOR, COORDINADOR
- **Descripción**: el usuario ve las tareas que le fueron asignadas, filtradas por contexto académico. Puede iniciar el flujo de delegación o elevar la tarea a coordinación.

### F8.2 — Asignar tarea a otro docente

- **Quién**: PROFESOR, COORDINADOR
- **Descripción**: permite delegar una tarea a otro miembro del equipo docente, dejando trazabilidad del asignador y el asignado.

### F8.3 — Administración de tareas (coordinación)

- **Quién**: COORDINADOR, ADMIN
- **Descripción**: vista global de todas las tareas del tenant con filtros por docente asignado, docente asignador, materia, estado y búsqueda libre.
- **Acciones**: cambiar el estado de una tarea y agregar comentarios como parte del workflow asincrónico.

---

## Épica 9 — Auditoría y Métricas de Uso

### F9.1 — Panel de interacciones del sistema

- **Quién**: ADMIN, COORDINADOR (con permiso `auditoria:ver`)
- **Sub-vistas**:
  - Gráfico de acciones por día (volumen de uso temporal).
  - Estado de comunicaciones agrupado por docente (Pendiente / En envío / Enviado / Fallido / Cancelado).
  - Interacciones por docente y materia (métricas de uso por tipo de acción: análisis de desempeño, vista previa, importación, envío, limpieza de datos, configuración de umbral, emails generados, lotes procesados).
  - Log de últimas acciones (máximo configurable; por defecto 200 registros más recientes).
- **Filtros**: rango de fechas, materia, usuario, estado de actividad.

### F9.2 — Log completo de auditoría

- **Quién**: ADMIN
- **Campos registrados por cada acción**: fecha y hora, identificador de usuario, materia, tipo de acción, cantidad de registros afectados, dirección IP de origen, agente de usuario.
- **Reglas aplicadas**: [RN-23](05_reglas_de_negocio.md#rn-23), [RN-24](05_reglas_de_negocio.md#rn-24)

---

## Épica 10 — Liquidaciones y Honorarios

### F10.1 — Vista de liquidaciones del período

- **Quién**: FINANZAS, ADMIN
- **Descripción**: vista del cálculo de honorarios para todos los docentes del período seleccionado, con detalle de rol, comisiones a cargo, salario base, plus aplicables y total a cobrar.
- **Acciones disponibles**: vista previa del detalle individual, exportar, cerrar liquidación, acceder al historial, administrar la grilla salarial.

### F10.2 — Cerrar liquidación

- **Quién**: FINANZAS
- **Efecto**: convierte la liquidación del período en un registro inmutable. Una liquidación cerrada no puede modificarse.
- **Reglas aplicadas**: [RN-22](05_reglas_de_negocio.md#rn-22)

### F10.3 — Historial de liquidaciones

- **Quién**: FINANZAS, ADMIN
- **Descripción**: acceso al registro de liquidaciones cerradas de períodos anteriores para consulta y auditoría.

### F10.4 — Administración de grilla salarial

- **Quién**: FINANZAS (con permiso `liquidaciones:configurar-salarios`)
- **Descripción**: gestiona dos tablas con vigencia temporal:
  - **Salario base**: importe por rol (PROFESOR / TUTOR / NEXO / COORDINADOR) con fechas de vigencia desde / hasta.
  - **Plus**: incrementos adicionales identificados por clave, rol y descripción, también con vigencia.
- **Reglas aplicadas**: [RN-31](05_reglas_de_negocio.md#rn-31), [RN-32](05_reglas_de_negocio.md#rn-32), [RN-33](05_reglas_de_negocio.md#rn-33)

### F10.5 — Gestión de facturas de docentes que facturan

- **Quién**: FINANZAS
- **Descripción**: ABM de comprobantes presentados por docentes que trabajan bajo modalidad de facturación independiente (monotributo u equivalente).
- **Datos del comprobante**: fecha de carga, docente, período facturado, detalle, archivo adjunto, tamaño del archivo, estado, datos de pago.
- **Filtros**: docente, estado (pendiente / abonada), rango de fechas, búsqueda libre.
- **Acción principal**: cambiar el estado del comprobante entre pendiente y abonado.
- **Regla clave**: los docentes que facturan **no se incluyen** en la liquidación general — su pago se gestiona exclusivamente por este flujo.
- **Reglas aplicadas**: [RN-35](05_reglas_de_negocio.md#rn-35)

### F10.6 — Separación contable en la liquidación (factura vs. no-factura)

- **Quién**: FINANZAS, ADMIN
- **Descripción**: la vista de liquidación presenta tres segmentos diferenciados:
  1. **Detalle general**: roles PROFESOR, TUTOR y COORDINADOR que no facturan.
  2. **NEXO**: calculado por separado pero sumado al total general.
  3. **Docentes que facturan**: visualizados informativamente pero excluidos del total de liquidación; su pago se gestiona por [F10.5](#f105--gestión-de-facturas-de-docentes-que-facturan).
- **KPIs de cabecera**: "Total sin factura" y "Total con factura" para facilitar la toma de decisiones contables.
- **Filtros**: cohorte, mes, y opcionalmente un docente específico.
- **Reglas aplicadas**: [RN-35](05_reglas_de_negocio.md#rn-35), [RN-36](05_reglas_de_negocio.md#rn-36), [RN-37](05_reglas_de_negocio.md#rn-37), [RN-38](05_reglas_de_negocio.md#rn-38)

---

## Épica 11 — Perfil y Sesión

### F11.1 — Editar perfil propio

- **Quién**: cualquier usuario autenticado
- **Campos editables**: nombre, identificación fiscal, sexo, datos bancarios (banco, CBU / alias), regional, dirección de correo, modalidad de cobro (factura / liquidación), número de matrícula o registro profesional.
- **Campos de solo lectura**: CUIL u otro identificador fiscal principal (no modificable por el usuario).

### F11.2 — Bandeja de mensajes propia

- **Quién**: cualquier usuario autenticado
- **Capacidades**: ver hilos de mensajes recibidos y responder dentro del hilo.
- **Referencia**: ver [F3.4](#f34--mensajería-interna-bandeja-del-docente).

### F11.3 — Cierre de sesión

- **Quién**: cualquier usuario autenticado
- **Descripción**: el usuario termina su sesión de forma explícita. El sistema invalida la sesión activa y redirige al flujo de autenticación.

---

## Épica 12 — Integración con Módulo de Corrección Asistida

### F12.1 — Acceso al módulo de corrección asistida por IA

- **Quién**: PROFESOR, COORDINADOR (según permisos del tenant)
- **Descripción**: el sistema provee un acceso desde el menú principal hacia un módulo externo de corrección asistida por inteligencia artificial. Este módulo opera de forma independiente y su alcance funcional está fuera del scope de esta KB.
- **Estado**: módulo externo — no documentado en este catálogo.
