## ADDED Requirements

### Requirement: Log de últimas acciones protegido por permiso

El sistema SHALL exponer el log de últimas acciones de auditoría únicamente a usuarios con el permiso `auditoria:ver`. Las solicitudes sin ese permiso SHALL ser rechazadas con HTTP 403 (fail-closed). La identidad y el tenant del usuario SHALL resolverse exclusivamente desde la sesión autenticada (JWT), NUNCA desde la URL, el body ni un header. El log SHALL ser de solo lectura: no SHALL permitir crear, modificar ni eliminar eventos de auditoría.

#### Scenario: Usuario con permiso obtiene el log de últimas acciones
- **WHEN** un usuario con el permiso `auditoria:ver` solicita el log de últimas acciones
- **THEN** el sistema devuelve los eventos más recientes del tenant según el alcance de su permiso

#### Scenario: Usuario sin permiso es rechazado
- **WHEN** un usuario sin el permiso `auditoria:ver` solicita el log de últimas acciones
- **THEN** el sistema responde HTTP 403 y no devuelve ningún evento

### Requirement: Límite configurable del log con valor por defecto y tope acotado

El log de últimas acciones SHALL aceptar un parámetro `limite` que controla cuántos registros más recientes devolver. Cuando el parámetro se omita, el sistema SHALL usar el valor por defecto 200. El sistema SHALL definir un tope máximo configurable (`AUDIT_PANEL_LOG_MAX`, por defecto 200); un `limite` mayor que ese tope SHALL ser rechazado con HTTP 422 y no SHALL devolver registros. El `limite` SHALL ser un entero mayor o igual a 1. Los eventos SHALL devolverse ordenados por `created_at` descendente (más reciente primero).

#### Scenario: Límite por defecto cuando se omite el parámetro
- **WHEN** un usuario autorizado solicita el log sin especificar `limite`
- **THEN** el sistema devuelve como máximo 200 eventos, los más recientes primero

#### Scenario: Límite explícito dentro del tope
- **WHEN** un usuario autorizado solicita el log con `limite=50` (≤ tope)
- **THEN** el sistema devuelve como máximo 50 eventos, los más recientes primero

#### Scenario: Límite por encima del tope es rechazado
- **WHEN** un usuario autorizado solicita el log con un `limite` mayor que `AUDIT_PANEL_LOG_MAX`
- **THEN** el sistema responde HTTP 422 y no devuelve ningún evento

#### Scenario: Límite inválido es rechazado
- **WHEN** un usuario autorizado solicita el log con `limite=0` o un valor negativo
- **THEN** el sistema responde HTTP 422 y no devuelve ningún evento

### Requirement: Filtros del log completo de auditoría

El log de últimas acciones SHALL soportar los filtros del panel (F9.2, RN-23/RN-24): rango de fechas (`desde`/`hasta` sobre `created_at`), materia (derivada de `entidad_id` con `entidad_tipo = "Materia"`) y usuario (`actor_user_id`). Los filtros SHALL ser combinables y SHALL aplicarse en la consulta SQL del repository, scoped al tenant. Un evento SHALL incluirse solo si satisface todos los filtros activos.

#### Scenario: Filtro por rango de fechas
- **WHEN** un usuario autorizado solicita el log con `desde` y `hasta`
- **THEN** el sistema devuelve únicamente eventos cuyo `created_at` cae dentro del rango

#### Scenario: Filtro por usuario
- **WHEN** un usuario autorizado solicita el log filtrando por un `actor_user_id`
- **THEN** el sistema devuelve únicamente eventos de ese actor

#### Scenario: Filtro por materia
- **WHEN** un usuario autorizado solicita el log filtrando por un identificador de materia
- **THEN** el sistema devuelve únicamente eventos cuyo `entidad_tipo = "Materia"` y `entidad_id` coincide con la materia solicitada

#### Scenario: Filtros combinados
- **WHEN** un usuario autorizado solicita el log con rango de fechas y `actor_user_id` simultáneamente
- **THEN** el sistema devuelve únicamente eventos que satisfacen ambos filtros

### Requirement: Alcance row-level del log según el permiso

El log de últimas acciones SHALL respetar el alcance del permiso `auditoria:ver`. Con alcance `propio`, SHALL devolver únicamente los eventos cuyo actor real es el usuario actual; con alcance global, SHALL devolver todos los eventos del tenant. El alcance SHALL aplicarse en conjunto con los demás filtros y nunca SHALL exponer eventos de otro tenant.

#### Scenario: Alcance propio devuelve solo eventos propios
- **WHEN** un usuario cuyo permiso `auditoria:ver` tiene alcance `propio` solicita el log
- **THEN** el sistema devuelve únicamente eventos cuyo actor real es ese usuario

#### Scenario: Alcance global devuelve todos los eventos del tenant
- **WHEN** un usuario cuyo permiso `auditoria:ver` tiene alcance global solicita el log
- **THEN** el sistema devuelve todos los eventos del tenant, independientemente del actor

### Requirement: Contrato estricto de salida del log

El log SHALL devolver cada evento mediante un esquema de salida Pydantic v2 que rechaza campos no declarados (`extra='forbid'`). El esquema SHALL exponer los campos del evento de auditoría (fecha/hora, actor, acción, módulo, entidad, resultado, registros afectados, IP, user-agent) sin filtrar PII en texto plano (los payloads `before`/`after` ya vienen redactados desde C-05).

#### Scenario: Respuesta del log con esquema estricto
- **WHEN** un usuario autorizado solicita el log de últimas acciones
- **THEN** el sistema devuelve los eventos validados contra el esquema de salida, sin campos adicionales no declarados
