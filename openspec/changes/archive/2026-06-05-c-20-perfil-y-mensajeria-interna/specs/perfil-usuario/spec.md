## ADDED Requirements

### Requirement: Ver el perfil propio

El sistema SHALL exponer `GET /api/v1/perfil` para que un usuario autenticado obtenga sus propios datos de perfil. La identidad del usuario SHALL derivarse exclusivamente del JWT verificado; el endpoint SHALL NO aceptar ningún `usuario_id` por URL, query o body. La PII descifrada (`dni`, `cbu`, `alias_cbu`, `cuil`) SHALL devolverse en texto plano al propio dueño del perfil, ya que es su propio dato.

#### Scenario: Usuario lee su propio perfil
- **WHEN** un usuario autenticado invoca `GET /api/v1/perfil`
- **THEN** el sistema responde 200 con los datos del usuario cuyo `id` coincide con el `sub` del JWT
- **AND** los campos PII (`dni`, `cbu`, `alias_cbu`, `cuil`) se devuelven descifrados en texto plano

#### Scenario: Sin sesión no hay perfil
- **WHEN** se invoca `GET /api/v1/perfil` sin un JWT válido
- **THEN** el sistema responde 401 sin devolver datos

#### Scenario: La identidad nunca proviene de la petición
- **WHEN** un usuario invoca `GET /api/v1/perfil?usuario_id=<otro>`
- **THEN** el sistema ignora `usuario_id` y devuelve el perfil del titular del JWT

### Requirement: Editar el perfil propio

El sistema SHALL exponer `PATCH /api/v1/perfil`, protegido por `require_permission("perfil:editar")` (fail-closed: sin permiso → 403), para que el usuario actualice **sus propios** campos editables: `nombre`, `apellidos`, `dni`, `genero`, `banco`, `cbu`, `alias_cbu`, `regional`, `email`, `facturador` y `legajo_profesional`. El target SHALL ser siempre el titular del JWT. El schema de entrada SHALL ser Pydantic v2 con `extra='forbid'`.

#### Scenario: Edición de campos editables persiste
- **WHEN** un usuario con `perfil:editar` envía `PATCH /api/v1/perfil` con `banco`, `cbu` y `regional` nuevos
- **THEN** el sistema responde 200 y persiste los nuevos valores para el usuario del JWT
- **AND** la PII (`cbu`) queda cifrada en reposo (AES-256), nunca en texto plano en la base

#### Scenario: Sin permiso de edición se rechaza
- **WHEN** un usuario sin `perfil:editar` invoca `PATCH /api/v1/perfil`
- **THEN** el sistema responde 403 sin modificar ningún dato

#### Scenario: Campo no declarado es rechazado
- **WHEN** el body del PATCH incluye una clave no declarada en el schema (por ejemplo `tenant_id` o `estado`)
- **THEN** el sistema responde 422 (`extra='forbid'`) y no persiste cambios

#### Scenario: Un usuario no puede editar el perfil de otro
- **WHEN** un usuario envía un `PATCH /api/v1/perfil` con un `id` o `usuario_id` de otro usuario en el body
- **THEN** el sistema ignora ese identificador y aplica los cambios únicamente al titular del JWT

### Requirement: El CUIL es de solo lectura en el perfil

El sistema SHALL tratar el `cuil` como campo de solo lectura del perfil. El `PATCH /api/v1/perfil` SHALL NO permitir modificar `cuil`; el schema de actualización NO SHALL declarar ese campo como editable.

#### Scenario: Intento de editar CUIL es rechazado
- **WHEN** el body del PATCH incluye `cuil`
- **THEN** el sistema responde 422 (campo no permitido por `extra='forbid'`) y el `cuil` almacenado no cambia

#### Scenario: CUIL visible en lectura
- **WHEN** el usuario lee su perfil vía `GET /api/v1/perfil`
- **THEN** el `cuil` se incluye en la respuesta en modo solo lectura

### Requirement: Unicidad de email al actualizar el perfil

El sistema SHALL preservar la unicidad `(tenant_id, email)` al actualizar el `email` del perfil, reusando el blind index determinístico (`email_hash`) definido en la capability `usuarios`. Un email ya usado por otro usuario activo del mismo tenant SHALL ser rechazado.

#### Scenario: Email duplicado en el tenant es rechazado
- **WHEN** un usuario cambia su `email` por uno ya usado por otro usuario activo del mismo tenant
- **THEN** el sistema responde 409 (conflicto) y no actualiza el email

#### Scenario: Cambio a email libre es aceptado
- **WHEN** un usuario cambia su `email` por uno no usado en su tenant
- **THEN** el sistema responde 200 y actualiza el `email` y su `email_hash`

### Requirement: Aislamiento multi-tenant del perfil

El sistema SHALL garantizar que toda lectura y escritura de perfil opere únicamente sobre el `Usuario` del tenant del JWT. El repositorio SHALL filtrar por `tenant_id` por defecto.

#### Scenario: El perfil nunca cruza tenants
- **WHEN** un usuario del tenant A opera sobre su perfil
- **THEN** ninguna consulta alcanza usuarios del tenant B, ni siquiera ante colisión de `id` entre tenants

### Requirement: La edición de perfil queda auditada

El sistema SHALL registrar cada actualización de perfil como un evento de auditoría con el `usuario_id` del titular (derivado del JWT), el código de acción correspondiente y la cantidad de registros afectados, sin incluir PII en texto plano en el registro.

#### Scenario: PATCH genera registro de auditoría sin PII
- **WHEN** un usuario actualiza su perfil exitosamente
- **THEN** se crea un evento de auditoría atribuido al titular del JWT
- **AND** el registro NO contiene en texto plano los valores de `dni`, `cuil`, `cbu` ni `alias_cbu`
