# usuarios Specification

## Purpose
TBD - created by archiving change usuarios-y-asignaciones. Update Purpose after archive.
## Requirements
### Requirement: Identidad de usuario por UUID interno

El sistema SHALL identificar a cada `Usuario` por un UUID interno opaco. El número de `legajo`, cuando exista, SHALL ser un atributo de negocio opcional y NUNCA actuar como clave primaria, credencial de acceso ni selector de sesión.

#### Scenario: Usuario sin legajo
- **WHEN** se da de alta un usuario sin `legajo`
- **THEN** el usuario se crea correctamente identificado por su UUID interno

#### Scenario: Legajo no es credencial
- **WHEN** dos usuarios del mismo tenant comparten un `legajo` nulo
- **THEN** ambos coexisten porque la identidad es el UUID, no el legajo

### Requirement: PII cifrada en reposo (AES-256)

El sistema SHALL almacenar los atributos sensibles del usuario (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) cifrados en reposo con AES-256. La capa de aplicación SHALL ver siempre el texto plano; la columna en la base de datos SHALL contener siempre el valor cifrado.

#### Scenario: PII se persiste cifrada
- **WHEN** se crea un usuario con `dni` y `cbu`
- **THEN** los valores almacenados en la base de datos están cifrados y no coinciden con el texto plano de entrada

#### Scenario: PII se descifra al leer por la app
- **WHEN** el service lee un usuario previamente creado
- **THEN** los atributos PII se devuelven en texto plano a la capa de negocio

### Requirement: PII nunca expuesta en logs ni respuestas no autorizadas

El sistema SHALL evitar que la PII cifrada aparezca en logs, mensajes de error o respuestas HTTP más allá de lo que el contrato del endpoint autoriza explícitamente.

#### Scenario: PII ausente de logs
- **WHEN** se ejecuta cualquier operación sobre un usuario
- **THEN** los logs estructurados NO contienen el valor en texto plano de `dni`, `cuil`, `cbu`, `alias_cbu` ni `email`

#### Scenario: Read schema controla la exposición
- **WHEN** un endpoint devuelve un usuario
- **THEN** el schema de salida solo incluye los campos autorizados por su contrato y nunca expone `tenant_id` como editable

#### Scenario: UsuarioRead no expone PII financiera en texto plano
- **WHEN** el ABM general (`/api/v1/admin/usuarios`) devuelve un usuario vía `UsuarioRead`
- **THEN** la respuesta contiene solo `id`, `email`, `nombre`, `apellidos`, `legajo`, `estado`, el resumen de asignaciones/roles y timestamps
- **AND** los campos `dni`, `cuil`, `cbu` y `alias_cbu` están ausentes en texto plano (omitidos o, a lo sumo, enmascarados como últimos dígitos `****1234`)
- **AND** el plaintext de esa PII financiera tampoco aparece en los logs de la operación

### Requirement: Unicidad de email por tenant vía blind index

El sistema SHALL garantizar que el par `(tenant_id, email)` sea único, usando un índice ciego determinístico (`email_hash`) calculado sobre el email normalizado. El email cifrado SHALL NO ser consultable en texto plano.

#### Scenario: Email duplicado en el mismo tenant es rechazado
- **WHEN** se intenta crear un segundo usuario con un email ya usado por otro usuario activo del mismo tenant
- **THEN** la operación es rechazada con conflicto (409) y el segundo usuario no se persiste

#### Scenario: Mismo email en tenants distintos es válido
- **WHEN** dos tenants distintos crean usuarios con el mismo email
- **THEN** ambos usuarios se crean correctamente (la unicidad es por tenant)

#### Scenario: Reuso de email tras baja lógica
- **WHEN** un usuario es dado de baja lógica y luego se crea otro con el mismo email en el mismo tenant
- **THEN** la creación es aceptada (la unicidad aplica solo a filas no borradas)

### Requirement: ABM de usuarios protegido para ADMIN

El sistema SHALL exponer el alta, edición, activación/desactivación y baja lógica de usuarios bajo `/api/v1/admin/usuarios`, exigiendo el permiso `usuarios:gestionar`. Sin ese permiso, el sistema SHALL responder 403 (fail-closed). El `tenant_id` SHALL derivarse del JWT verificado, nunca del cuerpo de la petición.

#### Scenario: Acceso sin permiso es denegado
- **WHEN** un usuario sin `usuarios:gestionar` invoca cualquier operación de ABM de usuarios
- **THEN** el sistema responde 403 sin ejecutar la operación

#### Scenario: Alta con permiso deriva tenant del JWT
- **WHEN** un ADMIN con `usuarios:gestionar` crea un usuario
- **THEN** el usuario se crea en el tenant del JWT del ADMIN, ignorando cualquier `tenant_id` presente en el body

#### Scenario: Baja lógica conserva el registro
- **WHEN** un ADMIN da de baja un usuario
- **THEN** el registro se marca `deleted_at` (soft delete) y nunca se elimina físicamente

### Requirement: Aislamiento multi-tenant de usuarios

El sistema SHALL impedir que un usuario de un tenant lea o modifique usuarios de otro tenant. Toda consulta SHALL filtrar por `tenant_id` por defecto.

#### Scenario: Listado no cruza tenants
- **WHEN** un ADMIN del tenant A lista usuarios
- **THEN** la respuesta nunca incluye usuarios del tenant B

