## ADDED Requirements

### Requirement: Versioned student roster per materia×cohorte
The system SHALL maintain a versioned history of student rosters. Each import creates a new `VersionPadron` record. At most one version SHALL be active per `(tenant_id, materia_id, cohorte_id)` at any given time. Activating a new version SHALL atomically deactivate the previous one in the same database transaction.

#### Scenario: Activating new version deactivates previous
- **WHEN** a PROFESOR imports a new roster for materia M and cohorte C
- **THEN** the previously active `VersionPadron` for (M, C) has `activa = False`
- **AND** the new `VersionPadron` has `activa = True`
- **AND** the old entries remain in the database with their original `version_id`

#### Scenario: First import for a materia×cohorte has no previous version to deactivate
- **WHEN** a PROFESOR imports a roster for a materia×cohorte that has never been loaded
- **THEN** a `VersionPadron` is created with `activa = True`
- **AND** no prior version exists to deactivate

#### Scenario: Tenant isolation on versioned roster
- **WHEN** tenant A has an active roster for materia M and cohorte C
- **THEN** tenant B's roster for the same materia×cohorte is completely independent
- **AND** querying the active version always filters by `tenant_id`

---

### Requirement: Import preview before confirmation (two-step flow)
The system SHALL provide a preview of the parsed roster data WITHOUT writing to the database. Only after explicit confirmation SHALL the import be persisted and activated.

#### Scenario: Preview xlsx file returns parsed rows without saving
- **WHEN** a user with `padron:cargar` uploads a valid `.xlsx` file to the preview endpoint
- **THEN** the system returns a JSON payload with detected rows (nombre, apellidos, email, comision, regional)
- **AND** no `VersionPadron` or `EntradaPadron` is created in the database

#### Scenario: Preview csv file returns parsed rows without saving
- **WHEN** a user with `padron:cargar` uploads a valid `.csv` file to the preview endpoint
- **THEN** the system returns the same parsed JSON structure as for xlsx
- **AND** no database writes occur

#### Scenario: Malformed file returns 422 with validation details
- **WHEN** a user uploads a file with missing required columns (e.g., no email column)
- **THEN** the system returns HTTP 422 with a list of validation errors describing which columns are missing or malformed

#### Scenario: File exceeding maximum row limit returns 422
- **WHEN** a user uploads a file with more rows than `PADRON_MAX_ROWS` (default 5000)
- **THEN** the system returns HTTP 422 with a message indicating the row limit exceeded

---

### Requirement: Import confirmation creates and activates new version
Upon confirmation of a previewed payload, the system SHALL create a `VersionPadron` and all associated `EntradaPadron` records, then atomically activate the new version.

#### Scenario: Confirming preview creates VersionPadron and EntradaPadron records
- **WHEN** a user with `padron:cargar` sends a confirmed import payload
- **THEN** a new `VersionPadron` is created with `activa = True`, `cargado_por = current_user.id`, and the current timestamp
- **AND** one `EntradaPadron` is created per row in the payload

#### Scenario: EntradaPadron without usuario_id is allowed
- **WHEN** a roster row contains an email that does not match any existing `Usuario`
- **THEN** the `EntradaPadron` is created with `usuario_id = NULL`
- **AND** the import succeeds without error

#### Scenario: Audit event is recorded on successful activation
- **WHEN** a new version is activated successfully
- **THEN** an `AuditLog` record is created with `accion = 'PADRON_CARGAR'`, `actor_id = current_user.id`, `materia_id`, and `filas_afectadas = number of entries`

---

### Requirement: Scope-isolated clear of materia data (RN-04)
The system SHALL allow users to vacate (soft-delete) the active roster for a materia×cohorte. The scope of the clear operation is limited by the user's role.

#### Scenario: PROFESOR can only clear versions they loaded
- **WHEN** a PROFESOR requests to clear the roster for materia M and cohorte C
- **AND** the active `VersionPadron` was loaded by a different user
- **THEN** the system returns HTTP 403

#### Scenario: PROFESOR clears their own active version
- **WHEN** a PROFESOR requests to clear the roster for materia M and cohorte C
- **AND** the active `VersionPadron.cargado_por == current_user.id`
- **THEN** all `EntradaPadron` records of that version are soft-deleted (`deleted_at = now()`)
- **AND** the `VersionPadron` is set `activa = False` and soft-deleted

#### Scenario: COORDINADOR can clear any active version in their tenant
- **WHEN** a user with `padron:gestionar` requests to clear any materia×cohorte roster
- **THEN** the clear succeeds regardless of who loaded the active version

#### Scenario: Clear on materia with no active version returns 404
- **WHEN** a user requests to clear a roster for a materia×cohorte that has no active version
- **THEN** the system returns HTTP 404

---

### Requirement: Unauthorized access returns 403
The system SHALL reject all padron endpoints for users without the required permission, following the fail-closed RBAC policy.

#### Scenario: User without padron:cargar cannot import or preview
- **WHEN** a user without the `padron:cargar` permission calls any padron import endpoint
- **THEN** the system returns HTTP 403

#### Scenario: User without padron:gestionar cannot clear other users' versions
- **WHEN** a PROFESOR without `padron:gestionar` tries to clear a version loaded by another user
- **THEN** the system returns HTTP 403
