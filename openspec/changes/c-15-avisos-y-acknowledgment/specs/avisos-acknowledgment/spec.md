## ADDED Requirements

### Requirement: Any recipient can acknowledge an aviso (RN-19)
The system SHALL allow any authenticated user who can see an aviso (per audience and validity rules) to confirm having read it, creating an `AcknowledgmentAviso` with `confirmado_at`. The acknowledging `usuario_id` and `tenant_id` SHALL be resolved from the authenticated session, NEVER from the request body, URL or header. A user SHALL NOT be able to acknowledge an aviso they cannot see (out of audience, out of window, inactive, or soft-deleted).

#### Scenario: Recipient acknowledges a visible aviso
- **WHEN** a user who sees an aviso requiring ack confirms reading it
- **THEN** an `AcknowledgmentAviso` for that user and aviso is created with `confirmado_at` set

#### Scenario: Cannot acknowledge an aviso outside one's audience
- **WHEN** a user attempts to acknowledge an aviso whose audience does not include them
- **THEN** the system returns HTTP 403/404 and creates no acknowledgment

#### Scenario: Identity comes from the session, not the body
- **WHEN** an ack request body contains a `usuario_id` different from the authenticated user
- **THEN** the acknowledgment is created for the authenticated user and the body value is ignored

### Requirement: Acknowledgment is idempotent per user and aviso
The system SHALL allow at most one active `AcknowledgmentAviso` per (`tenant_id`, `aviso_id`, `usuario_id`). A second acknowledgment of the same aviso by the same user SHALL NOT create a duplicate row and SHALL succeed idempotently. This SHALL be enforced by a partial unique index on (`tenant_id`, `aviso_id`, `usuario_id`) `WHERE deleted_at IS NULL`.

#### Scenario: Double acknowledgment does not create a duplicate
- **WHEN** a user acknowledges the same aviso twice
- **THEN** exactly one `AcknowledgmentAviso` exists for that user and aviso

### Requirement: Acknowledged avisos drop off the pending view but still count
The system SHALL exclude an aviso requiring ack from a user's "pending" feed once that user has acknowledged it, while still keeping the aviso available in the full feed and still counting the acknowledgment toward the aviso's derived ack counter. An aviso with `requiere_ack = false` SHALL never appear in the pending view.

#### Scenario: After acknowledging, the aviso leaves the pending feed
- **WHEN** a user acknowledges an aviso that requires ack
- **THEN** that aviso no longer appears in the user's pending feed

#### Scenario: A non-ack aviso never appears as pending
- **WHEN** an in-window aviso has `requiere_ack = false`
- **THEN** it never appears in any user's pending feed

### Requirement: Ack counters are derived, not denormalized
The system SHALL compute an aviso's acknowledgment count by COUNTing the `AcknowledgmentAviso` rows for that aviso, scoped to the aviso's tenant and excluding soft-deleted rows. The count SHALL NOT be stored as a denormalized column on `Aviso`.

#### Scenario: Counter reflects current acknowledgments
- **WHEN** three distinct users have acknowledged an aviso
- **THEN** the aviso's derived ack count is 3

#### Scenario: Soft-deleted acknowledgment is not counted
- **WHEN** one of three acknowledgments is soft-deleted
- **THEN** the aviso's derived ack count is 2
