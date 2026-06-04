## ADDED Requirements

### Requirement: Threshold configuration per materia and asignación (RN-03)
The system SHALL allow a PROFESOR to configure the approval criterion for their own asignación in a materia. The criterion is a numeric threshold percentage (`umbral_pct`, default 60) and a set of textual values considered approving (`valores_aprobatorios`). The configuration SHALL be isolated to the configuring user's asignación and SHALL NOT affect any other docente's data in the same materia.

#### Scenario: Default threshold is 60 percent when not configured
- **WHEN** no `UmbralMateria` exists for a given asignación and materia
- **THEN** the effective `umbral_pct` used for `aprobado` derivation SHALL be 60
- **AND** the effective approving textual set SHALL be the tenant default ("Satisfactorio", "Supera lo esperado")

#### Scenario: PROFESOR configures a custom threshold for their asignación
- **WHEN** a PROFESOR with `calificaciones:configurar-umbral` sets `umbral_pct = 70` for their asignación in materia M
- **THEN** a `UmbralMateria` is created (or updated) with `umbral_pct = 70`, `asignacion_id = the profesor's asignación`, `materia_id = M`, and `tenant_id` from the session
- **AND** subsequent `aprobado` derivations for that asignación use 70 as the threshold

#### Scenario: Threshold of one docente does not affect another in the same materia
- **WHEN** PROFESOR A configures `umbral_pct = 80` and PROFESOR B configures `umbral_pct = 50` for the same materia M, each on their own asignación
- **THEN** `aprobado` for A's calificaciones is derived against 80
- **AND** `aprobado` for B's calificaciones is derived against 50
- **AND** neither configuration modifies the other's `UmbralMateria`

#### Scenario: Tenant isolation on threshold configuration
- **WHEN** tenant T1 has a `UmbralMateria` for asignación and materia
- **THEN** querying or updating thresholds in tenant T2 never reads or writes T1's records
- **AND** every threshold query filters by `tenant_id` from the session

---

### Requirement: Derivation of the aprobado field
The system SHALL derive the boolean `aprobado` of a `Calificacion` as a pure function of the grade and the effective approval criterion. A numeric grade is approving when it reaches the threshold percentage of the maximum possible grade; a textual grade is approving when it belongs to the configured approving set. The derivation SHALL be deterministic and free of side effects.

#### Scenario: Numeric grade at or above threshold is approved
- **WHEN** a `Calificacion` has `nota_numerica = 7` over a maximum of 10 and the effective `umbral_pct = 60`
- **THEN** `aprobado` SHALL be `True` (70% ≥ 60%)

#### Scenario: Numeric grade below threshold is not approved
- **WHEN** a `Calificacion` has `nota_numerica = 5` over a maximum of 10 and the effective `umbral_pct = 60`
- **THEN** `aprobado` SHALL be `False` (50% < 60%)

#### Scenario: Textual grade in the approving set is approved
- **WHEN** a `Calificacion` has `nota_textual = "Satisfactorio"` and no `nota_numerica`, with the approving set containing "Satisfactorio"
- **THEN** `aprobado` SHALL be `True`

#### Scenario: Textual grade outside the approving set is not approved
- **WHEN** a `Calificacion` has `nota_textual = "No alcanzado"` and no `nota_numerica`, with an approving set that does not contain "No alcanzado"
- **THEN** `aprobado` SHALL be `False`

#### Scenario: Numeric grade takes precedence over textual when both present
- **WHEN** a `Calificacion` has both `nota_numerica = 8` (max 10) and `nota_textual = "No alcanzado"`, with `umbral_pct = 60`
- **THEN** `aprobado` SHALL be derived from the numeric grade (`True`), per RN-03/RN-02 precedence of numeric grading

#### Scenario: Calificacion with neither numeric nor textual grade is not approved
- **WHEN** a `Calificacion` has `nota_numerica = NULL` and `nota_textual = NULL`
- **THEN** `aprobado` SHALL be `False`

---

### Requirement: Unauthorized threshold configuration returns 403
The system SHALL reject threshold configuration for users without the `calificaciones:configurar-umbral` permission, following the fail-closed RBAC policy.

#### Scenario: User without permission cannot configure a threshold
- **WHEN** a user without `calificaciones:configurar-umbral` calls the threshold configuration endpoint
- **THEN** the system returns HTTP 403

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to any umbral endpoint arrives without a valid JWT
- **THEN** the system returns HTTP 401
