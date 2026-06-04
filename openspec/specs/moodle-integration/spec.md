## ADDED Requirements

### Requirement: On-demand sync of enrolled users from Moodle WS
The system SHALL provide an endpoint to synchronize enrolled students from a Moodle course into a `VersionPadron`, using the Moodle Web Services API. This sync SHALL be triggered explicitly by a user with `padron:cargar` permission.

#### Scenario: Successful sync creates a new active VersionPadron
- **WHEN** a user with `padron:cargar` triggers an on-demand Moodle sync for a given `course_id`, `materia_id`, and `cohorte_id`
- **THEN** the system calls Moodle WS `core_enrol_get_enrolled_users` with the provided `course_id`
- **AND** a new `VersionPadron` is created and activated (deactivating the previous one)
- **AND** one `EntradaPadron` is created per enrolled student returned by Moodle
- **AND** an `AuditLog` record is created with `accion = 'PADRON_CARGAR'` and `filas_afectadas = number of enrolled users`

#### Scenario: Moodle WS returns an error on first attempt — system retries once
- **WHEN** Moodle WS returns an HTTP error or connection timeout on the first attempt
- **THEN** the system waits 2 seconds and retries the call exactly once
- **AND** if the retry also fails, the system raises a `502 Bad Gateway` response
- **AND** no `VersionPadron` or `EntradaPadron` is written to the database

#### Scenario: Moodle WS unavailable — 502 returned with descriptive message
- **WHEN** both attempts to reach Moodle WS fail
- **THEN** the system returns HTTP 502 with a JSON body describing the integration error
- **AND** the error message does not expose internal credentials or tokens

#### Scenario: Manual xlsx/csv import still works when Moodle WS is unavailable
- **WHEN** the Moodle WS client cannot reach the configured endpoint
- **THEN** the manual import flow (preview + confirm via file upload) continues to function independently
- **AND** the system does not return errors on the manual import endpoints due to Moodle unavailability

---

### Requirement: Nightly automatic sync background task
The system SHALL run a background task that automatically syncs enrolled users from Moodle for all configured course mappings, at a configurable UTC hour (`MOODLE_SYNC_HOUR`, default 3).

#### Scenario: Nightly task runs at the configured hour and syncs all mappings
- **WHEN** the configured sync hour is reached (UTC)
- **THEN** the background task iterates all tenant Moodle course mappings and calls the Moodle sync logic for each
- **AND** each successful sync creates a new active `VersionPadron` following the same rules as on-demand sync

#### Scenario: Nightly task failure for one mapping does not stop others
- **WHEN** the Moodle WS sync fails for one course mapping (after retries)
- **THEN** the task logs the error and continues processing remaining mappings
- **AND** the failure is recorded in the structured log (does not raise an unhandled exception)

---

### Requirement: Moodle WS client configuration per environment
The system SHALL read Moodle WS credentials from environment variables (`MOODLE_BASE_URL`, `MOODLE_TOKEN`) as defined in `Settings`. These values SHALL NOT appear in logs, error messages, or API responses.

#### Scenario: Missing Moodle configuration disables WS sync without breaking import
- **WHEN** `MOODLE_BASE_URL` or `MOODLE_TOKEN` is not set in the environment
- **THEN** the on-demand Moodle sync endpoint returns HTTP 503 with a message indicating the integration is not configured
- **AND** manual xlsx/csv import endpoints continue to work normally

#### Scenario: Moodle token never appears in logs or error responses
- **WHEN** a Moodle WS call fails for any reason
- **THEN** the structured log entry and the HTTP error response contain only the error description and status code
- **AND** the `MOODLE_TOKEN` value is never included in any log field or response body
