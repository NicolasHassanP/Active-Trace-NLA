## ADDED Requirements

### Requirement: Detection of numeric activity columns (RN-01)
When parsing a grades file exported from the LMS, the system SHALL interpret as a **numeric activity** only those columns whose header ends with the suffix `(Real)`. Any other column SHALL NOT be processed as a numeric grade.

#### Scenario: Column ending in (Real) is detected as numeric activity
- **WHEN** the grades file contains a column header `"Tarea 1 (Real)"`
- **THEN** the system detects an activity named `"Tarea 1"` of numeric scale
- **AND** the column values are parsed as `nota_numerica`

#### Scenario: Column without the (Real) suffix is not treated as numeric
- **WHEN** the grades file contains a column header `"Tarea 1"` without the `(Real)` suffix
- **THEN** the system does not parse that column as a numeric grade

#### Scenario: Identity, email and metadata columns are ignored as activities
- **WHEN** the grades file contains columns such as `"Nombre"`, `"Apellido(s)"`, `"Dirección de correo"`
- **THEN** none of these are detected as evaluable activities

---

### Requirement: Detection of textual activity columns (RN-02)
The system SHALL interpret columns containing the configured textual scale values (e.g., "Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado") as **textual activities**. The values "Satisfactorio" and "Supera lo esperado" SHALL count as approving; "No satisfactorio" and "No alcanzado" SHALL NOT.

#### Scenario: Column with textual scale values is detected as textual activity
- **WHEN** a column holds values from the configured textual scale (e.g., "Satisfactorio", "No alcanzado")
- **THEN** the system detects a textual activity and stores each cell as `nota_textual`

#### Scenario: Approving textual values map to aprobado true
- **WHEN** a textual cell value is "Satisfactorio" or "Supera lo esperado"
- **THEN** the resulting `Calificacion.aprobado` is `True`

#### Scenario: Non-approving textual values map to aprobado false
- **WHEN** a textual cell value is "No satisfactorio" or "No alcanzado"
- **THEN** the resulting `Calificacion.aprobado` is `False`

---

### Requirement: Import preview before persistence (two-step flow)
The system SHALL provide a preview of the detected activities and students from an uploaded grades file WITHOUT writing any `Calificacion` to the database. Persistence SHALL occur only after explicit confirmation that includes the selected activities.

#### Scenario: Preview returns detected activities without writing
- **WHEN** a user with `calificaciones:importar` uploads a valid grades file (`.xlsx` or `.csv`) to the preview endpoint
- **THEN** the system returns the list of detected activities (name, scale: numeric or textual) and the detected students
- **AND** no `Calificacion` record is created in the database

#### Scenario: Malformed file returns 422 with validation details
- **WHEN** a user uploads a file that cannot be parsed or lacks any student identity column
- **THEN** the system returns HTTP 422 with a description of the validation error

---

### Requirement: Activity selection on confirmation
Upon confirmation, the system SHALL persist `Calificacion` records ONLY for the activities the user explicitly selected to include in the analysis. Activities not selected SHALL NOT produce `Calificacion` records.

#### Scenario: Only selected activities are persisted
- **WHEN** a file detects activities A, B, and C, and the user confirms importing only A and C
- **THEN** `Calificacion` records are created for activities A and C
- **AND** no `Calificacion` record is created for activity B

#### Scenario: Each persisted calificacion links to an EntradaPadron and derives aprobado
- **WHEN** the import is confirmed for a selected numeric activity
- **THEN** one `Calificacion` is created per student row, linked to its `entrada_padron_id`, with `materia_id`, `actividad`, `nota_numerica`, `origen = 'Importado'`, `importado_at = now()`
- **AND** `aprobado` is derived against the effective threshold for the importing user's asignación

#### Scenario: Import is scope-isolated per user and materia (RN-04)
- **WHEN** PROFESOR A imports grades for materia M
- **THEN** the persisted `Calificacion` records are scoped to A's import and do not overwrite or remove grades imported by another docente for the same materia

#### Scenario: Audit event is recorded on successful import
- **WHEN** a grades import is confirmed successfully
- **THEN** an `AuditEvent` is created with `accion = 'CALIFICACIONES_IMPORTAR'`, `actor_user_id = current user`, `modulo = 'calificaciones'`, and `registros_afectados = number of Calificacion records created`

---

### Requirement: Completion report detects ungraded submissions (RN-07, RN-08)
The system SHALL accept the LMS activity-completion report and cross-reference it against imported grades to detect submissions that are completed by the student but have no grade recorded. This detection SHALL apply ONLY to textual-scale activities (RN-08); numeric-scale activities SHALL be excluded because absence of a numeric grade equals not-submitted, not pending-correction.

#### Scenario: Completed textual activity without grade is reported as pending correction
- **WHEN** the completion report marks a textual-scale activity as completed for a student
- **AND** no `Calificacion` with a `nota_textual` exists for that student and activity
- **THEN** the system reports that submission as a possible ungraded work, identified by student and activity

#### Scenario: Numeric-scale activities are excluded from the ungraded detection
- **WHEN** the completion report marks a numeric-scale activity as completed for a student with no recorded grade
- **THEN** that activity is NOT included in the possible-ungraded report (RN-08)

#### Scenario: Textual activity that already has a grade is not reported
- **WHEN** the completion report marks a textual activity as completed for a student
- **AND** a `Calificacion` with `nota_textual` already exists for that student and activity
- **THEN** that submission is NOT reported as ungraded

---

### Requirement: Unauthorized grade import returns 403
The system SHALL reject all calificaciones import endpoints for users without the required permission, following the fail-closed RBAC policy.

#### Scenario: User without calificaciones:importar cannot preview or import
- **WHEN** a user without the `calificaciones:importar` permission calls any calificaciones import endpoint
- **THEN** the system returns HTTP 403

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to any calificaciones endpoint arrives without a valid JWT
- **THEN** the system returns HTTP 401
