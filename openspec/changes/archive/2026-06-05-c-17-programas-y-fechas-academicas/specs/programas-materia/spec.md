## ADDED Requirements

### Requirement: Registro de programa de materia

El sistema SHALL permitir registrar un programa de materia asociado a una combinación única de materia × carrera × cohorte del tenant, con un título descriptivo y una `referencia_archivo` que el sistema trata como puntero opaco (no la interpreta ni valida su contenido). La operación SHALL requerir el permiso `estructura:gestionar` y SHALL registrarse en el log de auditoría con la acción `PROGRAMA_GESTIONAR`.

#### Scenario: Alta exitosa de programa

- **WHEN** un usuario con `estructura:gestionar` registra un programa con `materia_id`, `carrera_id`, `cohorte_id`, `titulo` y `referencia_archivo` válidos del propio tenant
- **THEN** el sistema persiste el `ProgramaMateria` con su `tenant_id` derivado de la sesión, devuelve 201 con el `id` generado y registra un evento de auditoría `PROGRAMA_GESTIONAR`

#### Scenario: Referencia de archivo opaca preservada sin transformación

- **WHEN** se registra un programa con `referencia_archivo` = `"blob://store/abc-123"`
- **THEN** el valor se persiste y se recupera idéntico, sin que el sistema lo interprete, abra ni valide como path de disco

#### Scenario: Sin permiso falla cerrado

- **WHEN** un usuario sin `estructura:gestionar` intenta registrar un programa
- **THEN** el sistema responde 403 y no persiste nada

#### Scenario: Programa duplicado para la misma combinación

- **WHEN** ya existe un programa activo para una combinación materia × carrera × cohorte y se intenta registrar otro para la misma combinación
- **THEN** el sistema rechaza la operación con un error de conflicto (409) y conserva el programa existente

### Requirement: Listado y baja de programas

El sistema SHALL permitir listar los programas activos del tenant, filtrables por materia, carrera y cohorte, y SHALL permitir dar de baja un programa mediante borrado lógico (soft delete), nunca físico. Una baja SHALL liberar la combinación para un nuevo registro.

#### Scenario: Listado filtrado por cohorte

- **WHEN** un usuario con `estructura:gestionar` lista programas filtrando por un `cohorte_id`
- **THEN** el sistema devuelve solo los programas activos de ese tenant y esa cohorte, excluyendo los dados de baja

#### Scenario: Baja lógica de programa

- **WHEN** un usuario con `estructura:gestionar` da de baja un programa existente
- **THEN** el sistema marca `deleted_at`, el programa deja de aparecer en los listados y registra auditoría `PROGRAMA_GESTIONAR`

#### Scenario: Re-alta tras baja

- **WHEN** un programa de una combinación fue dado de baja y se registra un nuevo programa para la misma combinación
- **THEN** el sistema acepta el alta porque la unicidad solo aplica a registros no borrados

### Requirement: Aislamiento por tenant de programas

El sistema SHALL impedir el acceso a programas de otro tenant. Todo query SHALL filtrar por el `tenant_id` de la sesión por defecto.

#### Scenario: No se accede a programa de otro tenant

- **WHEN** un usuario del tenant A solicita por `id` un programa que pertenece al tenant B
- **THEN** el sistema responde 404 como si no existiera, sin revelar datos de otro tenant
