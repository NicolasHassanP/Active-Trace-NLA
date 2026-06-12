## ADDED Requirements

### Requirement: Página de administración de usuarios del tenant

El sistema SHALL exponer la ruta `/admin/usuarios` que permite a un usuario ADMIN listar, crear, editar y dar de baja (soft delete) usuarios del tenant, consumiendo `/api/v1/admin/usuarios` (C-07). El gate SHALL ser fail-closed: solo ADMIN accede; cualquier otro rol SHALL recibir `Forbidden403`. La identidad y el `tenant_id` SHALL derivarse del JWT y NUNCA del body.

#### Scenario: ADMIN lista usuarios
- **WHEN** un usuario ADMIN navega a `/admin/usuarios`
- **THEN** el sistema muestra la tabla de usuarios activos del tenant vía `GET /api/v1/admin/usuarios`

#### Scenario: Usuario sin rol ADMIN intenta entrar
- **WHEN** un usuario sin rol ADMIN navega a `/admin/usuarios`
- **THEN** el sistema renderiza `Forbidden403` y no realiza ninguna petición

### Requirement: Contrato no-PII en la gestión de usuarios

El frontend de usuarios SHALL operar exclusivamente sobre los campos no-PII del contrato `UsuarioRead`/`UsuarioCreate`/`UsuarioUpdate` (id, email, nombre, apellidos, legajo, estado y flags como facturador). El frontend SHALL NOT recoger, mostrar ni enviar PII financiera (dni, cuil, cbu, alias_cbu); esos campos pertenecen al ámbito de finanzas (C-24).

#### Scenario: El formulario no expone PII financiera
- **WHEN** el ADMIN abre el formulario de alta o edición de usuario
- **THEN** el formulario no presenta campos de dni, cuil, cbu ni alias_cbu

#### Scenario: La tabla no muestra PII financiera
- **WHEN** el sistema renderiza la tabla de usuarios
- **THEN** ninguna columna expone dni, cuil, cbu ni alias_cbu

### Requirement: Alta, edición y baja lógica de usuarios

El sistema SHALL permitir crear (`POST`), editar (`PATCH` parcial) y dar de baja (`DELETE`, soft delete) usuarios. Los errores de dominio SHALL mostrarse vía `parseDomainError`.

#### Scenario: Crear un usuario
- **WHEN** el ADMIN completa el formulario de alta (email, nombre, apellidos, legajo, estado) y confirma
- **THEN** el sistema envía `POST /api/v1/admin/usuarios` y, al recibir 201, refresca la tabla

#### Scenario: Email duplicado
- **WHEN** el ADMIN intenta crear o editar un usuario con un email ya existente y el backend responde 409
- **THEN** el sistema muestra el mensaje de `ConflictoEmail` (vía `parseDomainError`) sin alterar la tabla

#### Scenario: Baja lógica de usuario
- **WHEN** el ADMIN confirma la baja de un usuario
- **THEN** el sistema envía `DELETE /api/v1/admin/usuarios/{id}` y, al recibir 204, el usuario desaparece de la lista de activos (soft delete en backend)
