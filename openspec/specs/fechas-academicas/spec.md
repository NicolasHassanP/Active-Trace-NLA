## ADDED Requirements

### Requirement: CRUD de fechas académicas

El sistema SHALL permitir crear, editar y dar de baja fechas académicas (instancias evaluativas) por materia × cohorte × número de instancia. Cada fecha SHALL tener un `tipo` (Parcial | TP | Coloquio | Recuperatorio), un `numero`, un `periodo`, una `fecha` y un `titulo`. Las operaciones SHALL requerir el permiso `estructura:gestionar` y SHALL registrarse en auditoría con la acción `FECHA_ACADEMICA_GESTIONAR`. La baja SHALL ser borrado lógico (soft delete), nunca físico.

#### Scenario: Alta exitosa de fecha académica

- **WHEN** un usuario con `estructura:gestionar` crea una fecha con `materia_id`, `cohorte_id`, `tipo`="Parcial", `numero`=1, `periodo`="2026-1", `fecha` y `titulo` válidos
- **THEN** el sistema persiste la `FechaAcademica` con `tenant_id` derivado de la sesión, devuelve 201 con su `id` y registra auditoría `FECHA_ACADEMICA_GESTIONAR`

#### Scenario: Edición de fecha existente

- **WHEN** un usuario con `estructura:gestionar` modifica la `fecha` o el `titulo` de una fecha académica existente
- **THEN** el sistema actualiza el registro, refresca `updated_at` y registra auditoría

#### Scenario: Baja lógica de fecha

- **WHEN** un usuario con `estructura:gestionar` da de baja una fecha académica
- **THEN** el sistema marca `deleted_at`, la fecha deja de aparecer en los listados y nunca se elimina físicamente

#### Scenario: Tipo inválido rechazado

- **WHEN** se intenta crear una fecha con `tipo` fuera del conjunto {Parcial, TP, Coloquio, Recuperatorio}
- **THEN** el sistema responde 422 y no persiste nada

#### Scenario: Duplicado de instancia rechazado

- **WHEN** ya existe una fecha activa para una combinación materia × cohorte × tipo × numero × periodo y se intenta crear otra igual
- **THEN** el sistema responde con conflicto (409) y conserva la existente

#### Scenario: Sin permiso falla cerrado

- **WHEN** un usuario sin `estructura:gestionar` intenta crear o editar una fecha académica
- **THEN** el sistema responde 403 y no persiste cambios

### Requirement: Listado tabular y vista calendario

El sistema SHALL exponer las fechas académicas activas del tenant en un listado filtrable por materia, cohorte, tipo y período. El sistema SHALL ofrecer una vista calendario que devuelve las mismas fechas ordenadas cronológicamente por `fecha`. Ningún dato del calendario SHALL denormalizarse: ambas vistas derivan de la misma consulta.

#### Scenario: Listado tabular filtrado

- **WHEN** un usuario con `estructura:gestionar` lista fechas filtrando por `materia_id` y `periodo`
- **THEN** el sistema devuelve solo las fechas activas de ese tenant que cumplen los filtros

#### Scenario: Vista calendario ordenada por fecha

- **WHEN** un usuario solicita la vista calendario para una materia × cohorte
- **THEN** el sistema devuelve las fechas activas ordenadas ascendentemente por `fecha`

### Requirement: Generación de fragmento de contenido para el LMS

El sistema SHALL generar un fragmento de contenido HTML con el calendario de fechas académicas de una materia × cohorte, listo para embeber en el aula virtual del LMS. Todo valor de texto incluido en el fragmento SHALL escaparse para prevenir inyección de HTML/XSS.

#### Scenario: Fragmento con fechas

- **WHEN** se solicita el fragmento de una materia × cohorte que tiene fechas activas
- **THEN** el sistema devuelve un fragmento HTML que lista cada fecha con su tipo, número, fecha y título

#### Scenario: Escapado de XSS

- **WHEN** una fecha tiene un `titulo` que contiene `<script>alert(1)</script>`
- **THEN** el fragmento generado emite el título escapado (sin etiquetas activas), sin ejecutar ni embeber HTML peligroso

#### Scenario: Fragmento sin fechas

- **WHEN** se solicita el fragmento de una materia × cohorte sin fechas activas
- **THEN** el sistema devuelve un fragmento HTML vacío bien formado (sin error)

### Requirement: Aislamiento por tenant de fechas académicas

El sistema SHALL impedir el acceso a fechas académicas de otro tenant. Todo query SHALL filtrar por el `tenant_id` de la sesión por defecto.

#### Scenario: No se accede a fecha de otro tenant

- **WHEN** un usuario del tenant A solicita por `id` una fecha académica del tenant B
- **THEN** el sistema responde 404 como si no existiera
