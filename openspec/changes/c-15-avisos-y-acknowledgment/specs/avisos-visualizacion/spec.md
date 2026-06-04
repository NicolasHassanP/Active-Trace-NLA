## ADDED Requirements

### Requirement: Recipient sees only avisos matching their audience (RN-20)
The system SHALL return to an authenticated user only the avisos whose audience includes them, evaluated against the user's role, cohorte and linked materias resolved from the authenticated session. The match rules are: `Global` matches every user; `PorRol` matches when the aviso's `rol_destino` equals one of the user's roles; `PorCohorte` matches when the aviso's `cohorte_id` equals the user's cohorte; `PorMateria` matches when the aviso's `materia_id` is a materia the user is linked to. All queries SHALL be scoped to the user's tenant and SHALL exclude soft-deleted avisos.

#### Scenario: Global aviso is shown to any user
- **WHEN** an active in-window Global aviso exists in the user's tenant
- **THEN** it appears in that user's feed regardless of role or cohorte

#### Scenario: PorRol aviso is shown only to the target role
- **WHEN** an aviso has `alcance = PorRol` and `rol_destino = PROFESOR`
- **THEN** it appears for a PROFESOR and does NOT appear for an ALUMNO

#### Scenario: PorCohorte aviso is shown only to that cohorte
- **WHEN** an aviso has `alcance = PorCohorte` for cohorte C1
- **THEN** it appears for a user in cohorte C1 and not for a user in cohorte C2

#### Scenario: PorMateria aviso is shown only to linked users
- **WHEN** an aviso has `alcance = PorMateria` for materia M1
- **THEN** it appears for a user linked to M1 and not for a user not linked to M1

#### Scenario: Avisos from another tenant are never shown
- **WHEN** an aviso exists in tenant T2
- **THEN** it never appears in the feed of a user in tenant T1

### Requirement: Only avisos inside their validity window are shown (RN-18)
The system SHALL include an aviso in a recipient's feed only when the current time is within `[inicio_en, fin_en]` and the aviso is `activo = true`. An aviso whose window has not started, has already ended, or is inactive SHALL NOT be shown, even though it still exists.

#### Scenario: Aviso not yet started is hidden
- **WHEN** an aviso has `inicio_en` in the future
- **THEN** it does not appear in any recipient feed

#### Scenario: Expired aviso is hidden
- **WHEN** an aviso has `fin_en` in the past
- **THEN** it does not appear in any recipient feed

#### Scenario: Aviso inside its window is shown
- **WHEN** the current time is between `inicio_en` and `fin_en` and `activo = true`
- **THEN** the aviso appears in the matching recipients' feed

### Requirement: Feed is ordered by priority
The system SHALL order a recipient's feed by `orden` (ascending = higher priority first) and then by `severidad` (Critico before Advertencia before Info) as a tie-breaker, so the highest-priority aviso appears first.

#### Scenario: Lower orden appears before higher orden
- **WHEN** two in-window matching avisos have `orden = 1` and `orden = 5`
- **THEN** the `orden = 1` aviso appears before the `orden = 5` aviso in the feed

#### Scenario: Severidad breaks ties on equal orden
- **WHEN** two in-window matching avisos share `orden = 1` with severidad `Critico` and `Info`
- **THEN** the `Critico` aviso appears before the `Info` aviso
