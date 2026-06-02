# 09 — Decisiones y Supuestos

> **Propósito**: registrar las decisiones de diseño del sistema activia-trace (D-XX) y los supuestos que el equipo debe validar antes o durante la implementación (S-XX). Este archivo es agnóstico de tecnología: describe el comportamiento esperado del producto, no una implementación concreta. El detalle técnico vive en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

---

## Decisiones de diseño (D-XX)

### D1 — El LMS es upstream (fuente de datos), no integración bidireccional automática
**Decisión**: el LMS es la **fuente de verdad** de calificaciones y actividad. El sistema **consume** esos datos por dos vías: (1) **web services del LMS** para sincronización automática, y (2) **importación manual de archivos exportados** (hoja de cálculo) como mecanismo de respaldo cuando los web services no están disponibles. El sistema **no escribe de vuelta al LMS de forma automática**.

**Por qué importa**: la sincronización automática reduce la desactualización; el import manual garantiza que el sistema funcione aun sin acceso programático al LMS. Las "salidas" hacia el LMS (por ejemplo, fragmentos de retroalimentación para pegar en el aula virtual) son responsabilidad del docente, que las copia manualmente. Ver [02 — Descripción General §3.1](02_descripcion_general.md) y [`ARQUITECTURA.md` §7.1](../docs/ARQUITECTURA.md).

---

### D2 — Identidad basada en UUID interno
**Decisión**: cada usuario se identifica mediante un **UUID opaco generado internamente**. Cualquier código o atributo institucional (número de legajo, número de documento, email) es un **atributo de negocio almacenado en el perfil**, no la identidad del sistema.

**Por qué importa**: la identidad nunca se expone en URLs ni en parámetros de petición. Esto elimina una clase entera de vulnerabilidades de suplantación y hace al sistema agnóstico respecto de los esquemas de identificación de cada institución. Ver [03 — Actores y Roles §1](03_actores_y_roles.md#1-concepto-identidad-rol-y-tenant) y [`ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md).

---

### D3 — Scope de datos operativos por (usuario, materia)
**Decisión**: los datos importados (calificaciones, umbrales, configuraciones de detección) son **propios del par (docente, materia)**. Dos docentes de la misma materia pueden tener importaciones y configuraciones independientes, y cada uno opera sobre sus propios datos sin afectar los del otro.

**Por qué importa**: respeta la autonomía docente. El sistema no impone una vista consolidada por defecto; el COORDINADOR puede agregarlo desde su rol, pero el PROFESOR solo ve y opera sobre lo suyo.

---

### D4 — Importación de padrón es reemplazante (upsert por snapshot)
**Decisión**: al importar un nuevo padrón de alumnos para una materia y período, el padrón anterior de ese contexto se **reemplaza** por el nuevo. No hay acumulación histórica de padrones.

**Por qué importa**: simplifica el modelo de datos operativo. La consecuencia es que no hay trazabilidad de altas/bajas entre importaciones: solo existe el estado actual. El equipo de producto debe decidir si en el futuro se agrega historial de padrón; por ahora es un scope explícito fuera del sistema.

---

### D5 — Aprobación humana obligatoria para comunicaciones masivas
**Decisión**: entre la generación de un envío masivo de comunicaciones y su despacho efectivo existe **un paso explícito de aprobación** por un actor autorizado (COORDINADOR o ADMIN). El sistema no despacha comunicaciones masivas de forma automática.

**Por qué importa**: el sistema prioriza el control institucional sobre la velocidad. Previene errores de comunicación de alto impacto. Ver [RN-XX en 05 — Reglas de Negocio](05_reglas_de_negocio.md) y el flujo de comunicaciones en [07 — Flujos Principales](07_flujos_principales.md).

---

### D6 — Auditoría de toda acción significativa
**Decisión**: cada acción relevante del usuario se registra con: quién la ejecutó, cuándo, desde qué contexto, sobre qué recurso, y con qué resultado. El registro es inmutable y no puede ser borrado por ningún rol operativo.

**Por qué importa**: comportamiento necesario en entornos académicos regulados, donde puede haber disputas sobre calificaciones, comunicaciones o accesos. La auditoría es la base de la trazabilidad del sistema. Ver [`ARQUITECTURA.md` §6](../docs/ARQUITECTURA.md).

---

### D7 — Autorización mediante RBAC con permisos finos
**Decisión**: el modelo de permisos es **RBAC (Role-Based Access Control) con permisos atómicos por capacidad** (`modulo:accion`). No existe ningún flag binario de superusuario. Los roles del dominio son: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS.

**Por qué importa**: los permisos son explícitos, auditables y administrables como datos. Permite que una institución configure qué puede hacer cada rol sin cambiar código. Ver [03 — Actores y Roles §3](03_actores_y_roles.md#3-modelo-de-autorización-rbac-con-permisos-finos) y [`ARQUITECTURA.md` §5.2](../docs/ARQUITECTURA.md).

---

### D8 — Vigencia temporal por asignación
**Decisión**: cada asignación de un usuario a un contexto académico (materia, comisión, equipo) tiene una fecha **desde** y una fecha **hasta**. La validez se computa al momento de cada petición: si la fecha actual no cae dentro del rango, la asignación no otorga permisos, aunque el registro se conserva en el histórico.

**Por qué importa**: facilita la rotación natural entre cuatrimestres sin borrar el historial. El equipo puede auditar quién tuvo permisos sobre qué materia y en qué período. Ver [03 — Actores y Roles §5](03_actores_y_roles.md#5-vigencia-temporal-de-las-asignaciones).

---

### D9 — Clonado de equipos entre períodos como operación de primera clase
**Decisión**: el sistema ofrece una operación explícita de **"clonar equipo docente"** de un período a otro, creando nuevas asignaciones vigentes a partir de un conjunto existente. No es necesario reasignar cada docente manualmente al inicio de cada período.

**Por qué importa**: optimiza el caso de uso más frecuente al fin de cuatrimestre. Indica que el ciclo académico es una primitiva del dominio, no un detalle de configuración.

---

### D10 — Avisos con acuse de recibo obligatorio
**Decisión**: los avisos pueden marcarse como **de acuse de recibo requerido**. El sistema registra qué usuarios vieron el aviso y cuáles confirmaron explícitamente haberlo leído. Sin confirmación, el aviso queda pendiente para el usuario.

**Por qué importa**: permite trazabilidad de comunicaciones obligatorias (cambio de fechas, políticas académicas, novedades críticas). El COORDINADOR o ADMIN puede ver el estado de confirmación por usuario.

---

### D11 — Vista previa obligatoria antes de envío de comunicaciones
**Decisión**: ninguna comunicación (individual ni masiva) puede despacharse sin que el actor que la genera visualice primero el contenido final renderizado (asunto, cuerpo con variables reemplazadas).

**Por qué importa**: previene errores graves de comunicación: variables sin reemplazar, formato roto, destinatarios incorrectos. Es una guardia de calidad en el flujo, no solo una comodidad de UX.

---

### D12 — Exportación tabular como capacidad transversal
**Decisión**: toda vista tabular de datos operativos (alumnos atrasados, guardias, equipos, liquidaciones, comunicaciones) puede exportarse en un formato de hoja de cálculo estándar.

**Por qué importa**: las instituciones siguen usando hojas de cálculo para su operativa offline. La exportación no es opcional: es parte del contrato funcional del sistema. El formato concreto (CSV, XLSX, ODS) es una decisión de implementación; el comportamiento esperado es que el dato tabular sea descargable.

---

## Supuestos a validar (S-XX)

### S1 — Autenticación por credenciales propias del sistema
**Supuesto**: el sistema gestiona su propio flujo de autenticación (email + contraseña), con soporte opcional de segundo factor (TOTP u otro). Las sesiones se mantienen con mecanismo seguro definido en la capa técnica.

**Cómo validar**: confirmar con el equipo de arquitectura el mecanismo de sesión y si se integra con algún proveedor de identidad externo (SSO, LDAP, SAML). Ver [`ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md).

---

### S2 — El estado de vigencia de asignaciones se computa en tiempo real
**Supuesto**: los valores "Vigente" / "Vencida" de una asignación se calculan al momento de la consulta comparando las fechas de la asignación con la fecha actual del servidor. No se almacena un campo de estado que requiera actualización periódica.

**Cómo validar**: definir con el equipo técnico si hay algún proceso de fondo que materialice el estado, o si siempre es cómputo en línea.

---

### S3 — Catálogos de materias pueden corresponder a múltiples planes de estudio o carreras
**Supuesto**: un tenant puede tener grupos de materias que pertenecen a distintos planes de estudio o carreras. La relación materia ↔ carrera ↔ cohorte es parte del modelo de estructura académica.

**Cómo validar**: ver [10 — Preguntas Abiertas PA-01](10_preguntas_abiertas.md#pa-01) y confirmar con el área académica de la institución el alcance multi-carrera del sistema.

---

### S4 — El despacho de comunicaciones es asíncrono con cola de trabajos
**Supuesto**: los estados de una comunicación (Pendiente / Enviando / Enviado / Fallido / Cancelado) implican una cola persistente procesada por un trabajador desacoplado del ciclo petición-respuesta del usuario.

**Cómo validar**: confirmar con el equipo de arquitectura el mecanismo de encolamiento y reintento. Ver [`ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

---

### S5 — La grilla salarial es multidimensional
**Supuesto**: la grilla que alimenta el cálculo de liquidaciones cruza al menos dos dimensiones (por ejemplo, rol académico × unidad organizativa). Puede incluir dimensiones adicionales como antigüedad o período.

**Cómo validar**: revisar con el área de Finanzas los criterios actuales de cálculo y el nivel de personalización que se espera del sistema.

---

### S6 — El CUIL/identificador fiscal es un campo derivado del perfil
**Supuesto**: el identificador fiscal del docente (CUIL u equivalente) se calcula o se deriva de otros datos del perfil (número de documento + género) y se muestra en modo solo lectura, sin almacenarse como campo independiente.

**Cómo validar**: acordar con el área de Finanzas si el CUIL debe almacenarse directamente (ingresado por el usuario o importado) o computarse en base a otros atributos.

---

### S7 — El contexto de agrupación de tareas es configurable por institución
**Supuesto**: las tareas internas del sistema pueden agruparse por algún contexto superior (cohorte, carrera, cuatrimestre, programa). El nivel de agrupación puede variar entre instituciones.

**Cómo validar**: definir con el área académica qué jerarquía de contextos se usa para organizar el trabajo de los equipos docentes.

---

### S8 — Las comunicaciones personalizadas usan un motor de plantillas
**Supuesto**: el sistema dispone de un mecanismo de plantillas para generar comunicaciones personalizadas por destinatario, con variables reemplazables (nombre del alumno, materia, calificación, etc.). El motor concreto es una decisión de implementación.

**Cómo validar**: definir con el equipo de producto el conjunto de variables disponibles en plantillas y el flujo de gestión de plantillas (quién las crea, quién las aprueba).

---

### S9 — Los avisos pueden tener scope de materia identificado por código
**Supuesto**: cuando un aviso tiene alcance acotado a una materia, el sistema lo asocia mediante un código de materia (no por ID numérico interno), lo que facilita la portabilidad entre períodos y tenants.

**Cómo validar**: definir con el área académica el esquema de identificación de materias que se usará como referencia en avisos y comunicaciones.

---

### S10 — El rol TUTOR está diferenciado funcionalmente de PROFESOR y COORDINADOR
**Supuesto**: el rol TUTOR tiene un conjunto de capacidades propio que lo distingue del PROFESOR (no dicta clases, no importa calificaciones en modo titular) y del COORDINADOR (no gestiona equipos). Participa principalmente en seguimiento, guardias y asistencia.

**Cómo validar**: revisar la matriz de permisos en [03 — Actores y Roles §3.3](03_actores_y_roles.md#33-matriz-de-capacidades-por-rol) y confirmar con el área académica las responsabilidades específicas del tutor en cada institución.

---

### S11 — Los datos bancarios sensibles se almacenan con protección adicional
**Supuesto**: los datos bancarios del docente (CBU, alias, entidad bancaria) se almacenan con una capa de protección adicional (cifrado en reposo) independientemente del cifrado general de la base de datos.

**Cómo validar**: confirmar con el equipo de arquitectura la estrategia de cifrado de datos sensibles. Ver [`ARQUITECTURA.md` §6](../docs/ARQUITECTURA.md).

---

### S12 — Los recursos estáticos y las respuestas frecuentes se sirven con caché
**Supuesto**: el sistema implementa algún nivel de caché (assets, respuestas de API de solo lectura) para garantizar tiempos de carga aceptables bajo carga institucional normal.

**Cómo validar**: definir con el equipo de arquitectura la estrategia de caché y los SLAs de rendimiento esperados.

---

## Alcance explícito del producto (qué no hace el sistema en su versión base)

### A1 — El alumno es actor activo del sistema
A diferencia de versiones anteriores del concepto, el sistema **sí tiene una vista para el alumno**: puede consultar su propio estado académico, confirmar avisos y reservar instancias de evaluación. Ver [03 — Actores y Roles](03_actores_y_roles.md) y [06 — Funcionalidades](06_funcionalidades.md).

### A2 — No genera reuniones de videoconferencia automáticamente
El sistema registra URLs de reuniones (Meet, Zoom u otro) pero no crea ni gestiona reuniones directamente en plataformas externas. El docente ingresa la URL manualmente.

### A3 — No despacha comunicaciones sin aprobación previa
Toda comunicación masiva requiere aprobación explícita (ver D5). No existe despacho automático sin revisión humana.

### A4 — No mantiene historial de padrón entre importaciones
Cada importación reemplaza el padrón anterior del contexto (ver D4). El historial de cambios de padrón está fuera del alcance de la versión base.

### A5 — No expone API pública documentada en la versión base
Las operaciones del sistema se realizan a través de la interfaz de usuario. Una API pública consumible por terceros es un roadmap item, no un requerimiento de la versión base.

### A6 — No incluye analítica avanzada ni dashboards de tendencias
El panel del sistema es operativo: muestra el estado actual y lo sucedido en el período en curso. El análisis longitudinal, predicciones o reportes de tendencias quedan fuera del alcance de la versión base.
