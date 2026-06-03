## ADDED Requirements

### Requirement: Registro de eventos de auditoría append-only

El sistema SHALL registrar cada acción significativa como un evento de auditoría inmutable que incluye: actor real, tenant, código de acción, módulo, tipo e identificador de entidad afectada, resultado, cantidad de registros afectados, dirección IP, user-agent, estado anterior (before) y posterior (after) del cambio, y marca de tiempo de creación. Cada evento de auditoría SHALL pertenecer a exactamente un tenant.

#### Scenario: Registro de un evento significativo

- **WHEN** un servicio registra una acción significativa con actor, código de acción, módulo y resultado
- **THEN** el sistema persiste un evento de auditoría con `created_at` asignado por el sistema y `tenant_id` igual al tenant del actor

#### Scenario: El tenant del evento se fuerza desde el scope, nunca desde la entrada

- **WHEN** se intenta registrar un evento con un `tenant_id` distinto al del scope del repositorio
- **THEN** el sistema sobreescribe el `tenant_id` del evento con el del scope antes de persistir

### Requirement: Inmutabilidad de los registros de auditoría

Los eventos de auditoría SHALL ser inmutables: una vez creados, el sistema NO SHALL permitir actualizarlos ni borrarlos por ningún rol ni por ningún camino de código o de base de datos. El modelo de datos de auditoría NO SHALL exponer borrado lógico (`deleted_at`) ni actualización (`updated_at`).

#### Scenario: Intento de actualización rechazado a nivel de base de datos

- **WHEN** se intenta ejecutar un UPDATE sobre una fila de `audit_event`
- **THEN** la base de datos rechaza la operación con una excepción

#### Scenario: Intento de borrado rechazado a nivel de base de datos

- **WHEN** se intenta ejecutar un DELETE sobre una fila de `audit_event`
- **THEN** la base de datos rechaza la operación con una excepción

#### Scenario: El repositorio de auditoría no expone operaciones de mutación

- **WHEN** se inspecciona la interfaz del repositorio de auditoría
- **THEN** solo ofrece registrar (insertar) y leer eventos, y no ofrece ningún método de actualización ni de borrado

### Requirement: Redacción de PII y secretos en el contenido auditado

Al serializar el estado anterior (before) y posterior (after) de un cambio, el sistema SHALL redactar los valores de claves sensibles (entre ellas password, CBU, DNI, alias de CBU, tokens, secretos y hashes) de forma que nunca se almacenen en texto plano en el registro de auditoría. La redacción SHALL aplicarse también a estructuras anidadas.

#### Scenario: Redacción de datos sensibles en before/after

- **WHEN** se registra un evento cuyo `before` o `after` contiene una clave sensible (por ejemplo `cbu` o `password`)
- **THEN** el evento persistido reemplaza el valor de esa clave por un marcador de redacción y nunca almacena el valor original

#### Scenario: Redacción recursiva en estructuras anidadas

- **WHEN** una clave sensible aparece dentro de un objeto anidado en `before` o `after`
- **THEN** el sistema también redacta ese valor anidado

### Requirement: Aislamiento de tenant en la auditoría

Las lecturas de eventos de auditoría SHALL estar acotadas por tenant por defecto: un usuario nunca SHALL poder leer eventos de auditoría de otro tenant.

#### Scenario: No se filtran eventos de otro tenant

- **WHEN** un usuario del tenant A consulta la auditoría
- **THEN** el sistema solo devuelve eventos cuyo `tenant_id` es el del tenant A, y nunca eventos del tenant B
