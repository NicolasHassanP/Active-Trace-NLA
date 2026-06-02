# 04 — Modelo de Datos

> **Propósito**: describir el modelo conceptual de datos del sistema en lenguaje de dominio, agnóstico de tecnología y motor de base de datos. Define las entidades, sus atributos (con tipos genéricos) y las relaciones entre ellas. Es la referencia para cualquier equipo que diseñe el esquema de persistencia, independientemente de la tecnología elegida. El detalle técnico de implementación (motor, migraciones, índices, estrategia de tenant isolation) vive en [`docs/ARQUITECTURA.md` §6 y §8](../docs/ARQUITECTURA.md).

---

## Supuestos base del modelo

1. **Tenant como raíz**: toda entidad del sistema lleva `tenant_id`. Los repositorios filtran por tenant por defecto; ninguna consulta puede cruzar datos entre instituciones ([03 — Actores y Roles](03_actores_y_roles.md) §1).
2. **Identidad de usuario = UUID interno**: el sistema identifica a cada usuario con un identificador interno opaco (UUID). El número de legajo, si existe, es un **atributo de negocio opcional**, no una clave de identidad ni credencial de acceso.
3. **Padrón versionado**: la carga de un nuevo padrón no destruye el anterior; se registra como una versión nueva con marca temporal, conservando el historial completo.
4. **Catálogo único de materias por tenant**: una sola fuente de verdad para las materias; no existen catálogos paralelos ni duplicados.
5. **Datos sensibles cifrados en reposo**: los atributos marcados con `[cifrado]` deben almacenarse cifrados (el algoritmo concreto vive en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md)).
6. **Auditoría obligatoria**: toda acción significativa genera un registro en el log de auditoría (E-AUD).

---

## Entidades principales

### E1 — Carrera

Representa un programa académico ofrecido por la institución.

```
Carrera {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  codigo      : texto      — código corto único dentro del tenant (ej: "TUPAD")
  nombre      : texto      — nombre completo del programa
  estado      : enum       — Activa | Inactiva
}
```

**Reglas**:
- El par `(tenant_id, codigo)` es único.
- Una carrera inactiva no admite nuevas inscripciones ni cohortes abiertas.

---

### E2 — Cohorte

Representa una cohorte (camada / ingreso) de estudiantes dentro de una carrera.

```
Cohorte {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  carrera_id  : UUID       — FK → Carrera
  nombre      : texto      — denominación legible (ej: "AGO-2025", "MAR-2026")
  anio        : entero     — año de inicio
  vig_desde   : fecha      — inicio de vigencia
  vig_hasta   : fecha      — fin de vigencia (nulo = abierta)
  estado      : enum       — Activa | Inactiva
}
```

**Reglas**:
- El par `(tenant_id, carrera_id, nombre)` es único.

---

### E3 — Materia

Unidad del catálogo académico del tenant. Es la referencia única para todos los módulos que operan sobre materias (calificaciones, encuentros, guardias, etc.).

```
Materia {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  codigo      : texto      — código único dentro del tenant (ej: "PROG_I")
  nombre      : texto      — nombre completo (ej: "Programación I")
  estado      : enum       — Activa | Inactiva
}
```

**Reglas**:
- El par `(tenant_id, codigo)` es único.
- Una misma materia puede pertenecer a distintas carreras y cohortes a través de la entidad Asignación (E5).

---

### E4 — Usuario (identidad base)

Representa a cualquier persona que interactúa con el sistema, independientemente de su rol.

```
Usuario {
  id               : UUID       — clave interna (identidad principal)
  tenant_id        : UUID       — FK → Tenant
  nombre           : texto
  apellidos        : texto
  email            : texto      — único dentro del tenant; [cifrado]
  dni              : texto      — documento de identidad; [cifrado]
  cuil             : texto      — identificador tributario; [cifrado]
  cbu              : texto      — clave bancaria uniforme; [cifrado]
  alias_cbu        : texto      — alias bancario; [cifrado]
  banco            : texto
  regional         : texto      — delegación o sede de pertenencia (opcional)
  legajo           : texto      — número de legajo institucional (atributo de negocio, no PK; opcional)
  legajo_profesional: texto     — legajo en el colegio/registro profesional (opcional)
  facturador       : booleano   — indica si el usuario emite facturas (monotributo u otro)
  estado           : enum       — Activo | Inactivo
}
```

**Reglas**:
- El par `(tenant_id, email)` es único.
- Los roles se modelan en la entidad Asignación (E5) y en el catálogo de roles del tenant, no como un campo booleano en esta entidad.
- Los datos marcados `[cifrado]` no deben exponerse en logs ni en texto plano en ninguna capa.

---

### E5 — Asignación (Usuario ↔ Rol ↔ Contexto académico)

Vincula a un usuario con un rol dentro de un contexto académico concreto (materia, carrera, cohorte, comisión). Es el eje del modelo de autorización.

```
Asignacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  usuario_id      : UUID       — FK → Usuario
  rol             : enum       — PROFESOR | TUTOR | COORDINADOR | NEXO | ADMIN | FINANZAS
  materia_id      : UUID       — FK → Materia (nullable si el rol es de tenant global)
  carrera_id      : UUID       — FK → Carrera (nullable)
  cohorte_id      : UUID       — FK → Cohorte (nullable)
  comisiones      : lista<texto> — comisiones incluidas (puede ser vacía)
  responsable_id  : UUID       — FK → Usuario (quién supervisa: coordinador responsable; nullable)
  desde           : fecha      — inicio de vigencia de la asignación
  hasta           : fecha      — fin de vigencia (nulo = abierta)
  estado_vigencia : enum       — Vigente | Vencida (derivado por fechas, no almacenado)
}
```

**Reglas**:
- Una asignación vencida no otorga permisos, pero se conserva en el histórico (ver [03 — Actores y Roles](03_actores_y_roles.md) §5).
- Un usuario puede tener múltiples asignaciones con distintos roles, materias y períodos.
- `responsable_id` modela la jerarquía docente: a quién rinde cuentas el asignado.

---

### E6 — Padrón (versiones de alumnos por materia)

Registra los estudiantes habilitados para una materia en un período dado. El modelo es **versionado**: cada carga genera una nueva versión, conservando el histórico.

```
VersionPadron {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  materia_id      : UUID       — FK → Materia
  cohorte_id      : UUID       — FK → Cohorte
  cargado_por     : UUID       — FK → Usuario
  cargado_at      : fecha-hora
  activa          : booleano   — solo una versión activa por (materia, cohorte) en simultáneo
}

EntradaPadron {
  id              : UUID       — clave interna
  version_id      : UUID       — FK → VersionPadron
  tenant_id       : UUID       — FK → Tenant
  usuario_id      : UUID       — FK → Usuario (ALUMNO; puede ser nulo si aún no tiene cuenta)
  nombre          : texto      — nombre del estudiante (desnormalizado para histórico)
  apellidos       : texto
  email           : texto      — [cifrado]
  comision        : texto      — comisión a la que pertenece
  regional        : texto      — sede / delegación
}
```

**Reglas**:
- Al activar una nueva versión, la anterior se desactiva (no se borra).
- Una `EntradaPadron` puede existir antes de que el alumno tenga cuenta de usuario en el sistema.

---

### E7 — Calificación

Registra la nota o estado de un estudiante en una actividad evaluable de una materia.

```
Calificacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  entrada_padron_id: UUID      — FK → EntradaPadron
  materia_id      : UUID       — FK → Materia
  actividad       : texto      — nombre de la actividad evaluable
  nota_numerica   : decimal    — valor numérico (nulo si solo hay nota textual)
  nota_textual    : texto      — descripción cualitativa (ej: "Satisfactorio")
  aprobado        : booleano   — derivado: nota_numerica >= umbral OR nota_textual ∈ conjunto aprobatorio
  origen          : enum       — Importado | Manual
  importado_at    : fecha-hora
}
```

**Reglas de derivación del campo `aprobado`**:
- Si existe `nota_numerica`: se compara con el umbral configurado para esa materia (E8).
- Si solo existe `nota_textual`: se evalúa contra el conjunto de valores aprobatorios configurados (ej: "Satisfactorio", "Supera lo esperado").

---

### E8 — Umbral de aprobación por materia

Configuración del criterio de aprobación de una materia, por asignación docente.

```
UmbralMateria {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  asignacion_id   : UUID       — FK → Asignacion
  materia_id      : UUID       — FK → Materia
  umbral_pct      : entero     — porcentaje mínimo de aprobación (defecto: 60)
  valores_aprobatorios: lista<texto> — valores textuales que cuentan como aprobado
}
```

**Reglas**:
- El umbral aplica solo a los datos del docente asignado en esa materia; no afecta a otros docentes.
- Si no existe umbral configurado, se usa el valor por defecto del tenant.

---

### E9 — Slot de Encuentro

Plantilla que define la recurrencia de un encuentro sincrónico (clase virtual, reunión).

```
SlotEncuentro {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  asignacion_id   : UUID       — FK → Asignacion (quién crea el slot)
  materia_id      : UUID       — FK → Materia
  titulo          : texto
  hora            : hora       — horario del encuentro
  dia_semana      : enum       — Lunes | Martes | Miércoles | Jueves | Viernes | Sábado | Domingo
  fecha_inicio    : fecha      — inicio de la recurrencia
  cant_semanas    : entero     — cuántas instancias genera (0 si es fecha única)
  fecha_unica     : fecha      — alternativa a recurrencia: un encuentro puntual (nullable)
  meet_url        : texto      — enlace a la sala virtual
  vig_desde       : fecha
  vig_hasta       : fecha
}
```

---

### E10 — Instancia de Encuentro

Encuentro concreto, derivado de un slot o creado de forma independiente.

```
InstanciaEncuentro {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  slot_id         : UUID       — FK → SlotEncuentro (nullable si es independiente)
  materia_id      : UUID       — FK → Materia
  fecha           : fecha
  hora            : hora
  titulo          : texto
  estado          : enum       — Programado | Realizado | Cancelado
  meet_url        : texto
  video_url       : texto      — grabación posterior (nullable)
  comentario      : texto
}
```

---

### E11 — Guardia

Registro de una guardia de atención a alumnos, asignada a un tutor o docente.

```
Guardia {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  asignacion_id   : UUID       — FK → Asignacion (quién cubre la guardia)
  materia_id      : UUID       — FK → Materia
  carrera_id      : UUID       — FK → Carrera
  cohorte_id      : UUID       — FK → Cohorte
  dia             : enum       — día de la semana
  horario         : texto      — rango horario (ej: "14:00–14:45")
  estado          : enum       — Pendiente | Realizada | Cancelada
  comentarios     : texto
  creada_at       : fecha-hora
}
```

---

### E12 — Tarea interna

Tarea de seguimiento asignada entre roles del equipo docente o de coordinación.

```
Tarea {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  materia_id      : UUID       — FK → Materia (nullable si es de nivel institucional)
  asignado_a      : UUID       — FK → Usuario (quien debe resolver)
  asignado_por    : UUID       — FK → Usuario (quien asigna)
  estado          : enum       — Pendiente | En progreso | Resuelta | Cancelada
  descripcion     : texto
  contexto_id     : UUID       — referencia opcional a otra entidad del dominio (nullable)
}

ComentarioTarea {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  tarea_id        : UUID       — FK → Tarea
  autor_id        : UUID       — FK → Usuario
  texto           : texto
  creado_at       : fecha-hora
}
```

---

### E13 — Aviso

Notificación institucional dirigida a uno o más segmentos de usuarios.

```
Aviso {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  alcance         : enum       — Global | PorMateria | PorCohorte | PorRol
  materia_id      : UUID       — FK → Materia (nullable)
  cohorte_id      : UUID       — FK → Cohorte (nullable)
  rol_destino     : enum       — rol al que va dirigido (nullable = todos)
  severidad       : enum       — Info | Advertencia | Crítico
  titulo          : texto
  cuerpo          : texto enriquecido
  inicio_en       : fecha-hora — desde cuándo es visible
  fin_en          : fecha-hora — hasta cuándo es visible
  orden           : entero     — prioridad de presentación
  activo          : booleano
  requiere_ack    : booleano   — si el usuario debe confirmar haber visto el aviso
}

AcknowledgmentAviso {
  id              : UUID       — clave interna
  aviso_id        : UUID       — FK → Aviso
  usuario_id      : UUID       — FK → Usuario
  confirmado_at   : fecha-hora
}
```

**Reglas**:
- Los contadores de vistas y confirmaciones se derivan consultando `AcknowledgmentAviso`; no se almacenan como campos denormalizados.

---

### E14 — Evaluación (instancia de examen)

Instancia de evaluación formal (parcial, coloquio, recuperatorio).

```
Evaluacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  materia_id      : UUID       — FK → Materia
  cohorte_id      : UUID       — FK → Cohorte
  tipo            : enum       — Parcial | TP | Coloquio | Recuperatorio
  instancia       : texto      — denominación libre (ej: "Coloquio Final")
  dias_disponibles: entero     — ventana de inscripción en días
}

ReservaEvaluacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  evaluacion_id   : UUID       — FK → Evaluacion
  alumno_id       : UUID       — FK → Usuario (ALUMNO)
  fecha_hora      : fecha-hora
  estado          : enum       — Activa | Cancelada
}

ResultadoEvaluacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  evaluacion_id   : UUID       — FK → Evaluacion
  alumno_id       : UUID       — FK → Usuario
  nota_final      : texto      — puede ser numérica o cualitativa
}
```

---

### E15 — Fecha académica (parciales, TPs, coloquios)

Calendarización de instancias evaluativas dentro de un período académico.

```
FechaAcademica {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  materia_id  : UUID       — FK → Materia
  cohorte_id  : UUID       — FK → Cohorte
  tipo        : enum       — Parcial | TP | Coloquio | Recuperatorio
  numero      : entero     — número de instancia (1er parcial, 2do parcial, etc.)
  periodo     : texto      — cuatrimestre / año (ej: "2026-1")
  fecha       : fecha
  titulo      : texto
}
```

---

### E16 — Programa de materia (documento)

Documento oficial del programa de una materia para una carrera y cohorte.

```
ProgramaMateria {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  materia_id  : UUID       — FK → Materia
  carrera_id  : UUID       — FK → Carrera
  cohorte_id  : UUID       — FK → Cohorte
  titulo      : texto
  referencia_archivo: texto — referencia al archivo en el servicio de almacenamiento
  cargado_at  : fecha-hora
}
```

---

### E17 — Grilla salarial base

Define el monto base por rol docente con vigencia temporal.

```
SalarioBase {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  rol         : enum       — PROFESOR | TUTOR | NEXO | COORDINADOR (o ALL para valor global)
  monto       : decimal
  desde       : fecha      — inicio de vigencia
  hasta       : fecha      — fin de vigencia (nulo = vigente sin límite)
}
```

**Reglas**:
- Para calcular el salario base de un docente en un período, se busca el registro con `rol` coincidente y `desde <= período <= hasta`.
- Solo puede haber una entrada vigente por rol en un instante dado.

---

### E18 — Plus salarial

Complemento adicional al salario base, por grupo de materias y rol.

```
SalarioPlus {
  id          : UUID       — clave interna
  tenant_id   : UUID       — FK → Tenant
  grupo       : texto      — clave del grupo de materias (ej: "PROG", "BD")
  rol         : enum       — PROFESOR | TUTOR | NEXO | COORDINADOR
  descripcion : texto      — descripción legible del plus
  monto       : decimal
  desde       : fecha
  hasta       : fecha      — nullable
}
```

**Reglas**:
- Un docente puede acumular plus de distintos grupos si dicta materias de varios de ellos.
- La clave `grupo` mapea a un conjunto de materias (definido en configuración del tenant).

---

### E19 — Liquidación

Resumen de honorarios de un docente para un período, derivado de su grilla salarial.

```
Liquidacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  cohorte_id      : UUID       — FK → Cohorte
  periodo         : texto      — AAAA-MM
  usuario_id      : UUID       — FK → Usuario (docente liquidado)
  rol             : enum       — rol bajo el cual se liquida
  comisiones      : lista<texto> — comisiones que dan lugar a la liquidación
  monto_base      : decimal    — de SalarioBase vigente en el período
  monto_plus      : decimal    — suma de SalarioPlus aplicables
  total           : decimal    — monto_base + monto_plus
  es_nexo         : booleano   — indica liquidación de tipo NEXO (tratamiento diferenciado)
  excluido_por_factura: booleano — docente monotributista: no se paga por este canal
  estado          : enum       — Abierta | Cerrada
}
```

**Reglas**:
- Cuando `excluido_por_factura = true`, la liquidación no genera pago directo (el docente emite factura por su cuenta, ver E20).
- Al cerrar una liquidación, no puede modificarse.

---

### E20 — Factura

Documento de cobro emitido por docentes que facturan sus honorarios.

```
Factura {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  usuario_id      : UUID       — FK → Usuario (con facturador = true)
  periodo         : texto      — AAAA-MM
  detalle         : texto      — descripción libre del servicio facturado
  referencia_archivo: texto    — referencia al PDF en el servicio de almacenamiento
  tamano_kb       : decimal    — tamaño del archivo en KB
  estado          : enum       — Pendiente | Abonada
  cargada_at      : fecha-hora
  abonada_at      : fecha-hora — nullable hasta que se abone
}
```

---

### E21 — Cola de comunicaciones (emails)

Historial y estado de los mensajes enviados a alumnos desde el sistema.

```
Comunicacion {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  enviado_por     : UUID       — FK → Usuario (docente o coordinador que dispara el envío)
  materia_id      : UUID       — FK → Materia
  destinatario    : texto      — dirección de email del alumno; [cifrado]
  asunto          : texto
  cuerpo          : texto enriquecido
  estado          : enum       — Pendiente | Enviando | Enviado | Error | Cancelado
  lote_id         : UUID       — agrupa envíos masivos de una misma acción
  enviado_at      : fecha-hora — nullable hasta que se procese
}
```

---

### E-AUD — Log de auditoría

Registro inmutable de toda acción significativa realizada en el sistema.

```
AuditLog {
  id              : UUID       — clave interna
  tenant_id       : UUID       — FK → Tenant
  fecha_hora      : fecha-hora
  actor_id        : UUID       — FK → Usuario (quién realizó la acción)
  impersonado_id  : UUID       — FK → Usuario (nulo si no hay impersonación activa)
  materia_id      : UUID       — FK → Materia (nullable)
  accion          : texto      — código de la acción (ej: "CALIFICACIONES_IMPORTAR")
  detalle         : JSON       — contexto adicional de la acción
  filas_afectadas : entero     — cantidad de registros involucrados
  ip              : texto      — dirección IP del cliente
  user_agent      : texto      — agente de usuario
}
```

**Reglas**:
- Ningún registro del log puede modificarse ni eliminarse.
- Las acciones bajo impersonación registran tanto al actor real como al usuario impersonado (ver [03 — Actores y Roles](03_actores_y_roles.md) §4).

---

## Relaciones (ERD simplificado)

```
Tenant (1) ─── (N) Carrera
Tenant (1) ─── (N) Cohorte
Tenant (1) ─── (N) Materia
Tenant (1) ─── (N) Usuario

Carrera (1) ─── (N) Cohorte
Carrera (1) ─── (N) Asignacion

Cohorte (1) ─── (N) Asignacion
Cohorte (1) ─── (N) VersionPadron
Cohorte (1) ─── (N) Evaluacion
Cohorte (1) ─── (N) FechaAcademica
Cohorte (1) ─── (N) Liquidacion

Materia (1) ─── (N) Asignacion
Materia (1) ─── (N) VersionPadron
Materia (1) ─── (N) Calificacion
Materia (1) ─── (N) UmbralMateria
Materia (1) ─── (N) SlotEncuentro
Materia (1) ─── (N) Guardia
Materia (1) ─── (N) Tarea
Materia (1) ─── (N) Aviso
Materia (1) ─── (N) Evaluacion
Materia (1) ─── (N) FechaAcademica
Materia (1) ─── (N) ProgramaMateria
Materia (1) ─── (N) Comunicacion

Usuario (1) ─── (N) Asignacion
Usuario (1) ─── (N) UmbralMateria
Usuario (1) ─── (N) SlotEncuentro
Usuario (1) ─── (N) Guardia
Usuario (1) ─── (N) Tarea (asignado a)
Usuario (1) ─── (N) Tarea (asignado por)
Usuario (1) ─── (N) Comunicacion
Usuario (1) ─── (N) Liquidacion
Usuario (1) ─── (N) Factura
Usuario (1) ─── (N) AuditLog
Usuario (1) ─── (N) AcknowledgmentAviso
Usuario (1) ─── (N) ReservaEvaluacion

VersionPadron (1) ─── (N) EntradaPadron
EntradaPadron (1) ─── (N) Calificacion

Asignacion (N) ─── (1) Asignacion   — jerarquía (responsable_id)
Asignacion (1) ─── (N) UmbralMateria
Asignacion (1) ─── (N) SlotEncuentro
Asignacion (1) ─── (N) Guardia

SlotEncuentro (1) ─── (N) InstanciaEncuentro

Tarea (1) ─── (N) ComentarioTarea

Aviso (1) ─── (N) AcknowledgmentAviso

Evaluacion (1) ─── (N) ReservaEvaluacion
Evaluacion (1) ─── (N) ResultadoEvaluacion
```

---

## Datos de referencia (seed típico)

Estos valores son ejemplos de datos iniciales esperados en una instalación. No son exhaustivos ni deben considerarse fijos:

| Entidad | Ejemplo |
|---------|---------|
| Carrera | Una o más carreras activas por tenant |
| Cohorte | Múltiples cohortes por carrera (típicamente 2 por año: inicio de primer y segundo cuatrimestre) |
| Materia | El tenant define su catálogo completo; típicamente decenas de materias |
| SalarioBase | Un registro por rol activo, con vigencia desde la fecha de acuerdo |
| SalarioPlus | Uno o más registros por grupo de materias × rol |

---

## Códigos de acción del log de auditoría

El campo `accion` del `AuditLog` usa un código textual estandarizado por módulo. Ejemplos representativos:

| Código | Descripción |
|--------|-------------|
| `CALIFICACIONES_IMPORTAR` | Importación de calificaciones desde archivo externo |
| `PADRON_CARGAR` | Carga de nueva versión del padrón |
| `COMUNICACION_ENVIAR` | Envío de comunicación a alumnos |
| `ASIGNACION_MODIFICAR` | Modificación de un equipo docente |
| `LIQUIDACION_CERRAR` | Cierre de una liquidación mensual |
| `IMPERSONACION_INICIAR` | Inicio de sesión de impersonación |
| `IMPERSONACION_FINALIZAR` | Fin de sesión de impersonación |

El catálogo completo de códigos es administrable y debe mantenerse en la documentación técnica.

---

## Convenciones del modelo

| Convención | Significado |
|------------|-------------|
| `_id` | Clave foránea a otra entidad |
| `tenant_id` | Toda entidad lo lleva; es la raíz del aislamiento |
| `vig_desde` / `vig_hasta` | Rango de vigencia temporal; `vig_hasta` nulo = abierto |
| `desde` / `hasta` | Igual que `vig_*`, en entidades que usan esa nomenclatura |
| `estado` | Enum de ciclo de vida del registro |
| `[cifrado]` | El atributo debe almacenarse cifrado en reposo |
| `referencia_archivo` | Puntero opaco al servicio de almacenamiento (no un path de disco) |
