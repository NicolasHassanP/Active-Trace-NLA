## ADDED Requirements

### Requirement: Página de administración de estructura académica

El sistema SHALL exponer la ruta `/admin/estructura` que permite a un usuario ADMIN administrar (ABM) carreras, materias y cohortes del tenant, consumiendo los endpoints `/api/v1/admin/{carreras,materias,cohortes}` (C-06). La identidad y el `tenant_id` SHALL derivarse siempre del JWT y NUNCA enviarse en el body. Todo fetch SHALL pasar por hooks de la capa `services/`; ningún componente SHALL llamar a `apiClient` directamente.

#### Scenario: ADMIN abre la página de estructura
- **WHEN** un usuario con rol ADMIN navega a `/admin/estructura`
- **THEN** el sistema carga y muestra los catálogos de carreras, materias y cohortes del tenant vía `GET /api/v1/admin/carreras|materias|cohortes`

#### Scenario: Usuario sin rol ADMIN intenta entrar
- **WHEN** un usuario sin rol ADMIN navega a `/admin/estructura`
- **THEN** el sistema renderiza `Forbidden403` y no realiza ninguna petición de gestión (fail-closed)

### Requirement: ABM de carreras, materias y cohortes

El sistema SHALL permitir crear, editar y dar de baja (soft delete) carreras, materias y cohortes desde la UI, mapeando cada acción a su endpoint (`POST`/`PATCH`/`DELETE`). La creación de cohorte SHALL requerir `carrera_id` y permitir `vig_hasta` nula (cohorte abierta). Los errores de dominio del backend SHALL mostrarse al usuario mediante `parseDomainError`.

#### Scenario: Crear una carrera
- **WHEN** el ADMIN completa el formulario de alta de carrera (codigo, nombre) y confirma
- **THEN** el sistema envía `POST /api/v1/admin/carreras` y, al recibir 201, refresca la tabla de carreras

#### Scenario: Conflicto de unicidad al crear
- **WHEN** el ADMIN intenta crear una carrera/materia/cohorte con un código duplicado y el backend responde 409
- **THEN** el sistema muestra el mensaje de error de dominio devuelto (vía `parseDomainError`) sin agregar la fila

#### Scenario: Crear una cohorte abierta
- **WHEN** el ADMIN crea una cohorte con `carrera_id`, `nombre`, `anio`, `vig_desde` y deja `vig_hasta` vacío
- **THEN** el sistema envía `POST /api/v1/admin/cohortes` con `vig_hasta` nula y la cohorte queda registrada como abierta

#### Scenario: Dar de baja una entidad
- **WHEN** el ADMIN confirma la baja de una carrera, materia o cohorte
- **THEN** el sistema envía el `DELETE` correspondiente y, al recibir 204, la entidad desaparece de la tabla (soft delete en backend)
