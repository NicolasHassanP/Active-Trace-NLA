## ADDED Requirements

### Requirement: Consulta paginada del historial de envíos propios
El sistema SHALL exponer `GET /api/v1/comunicaciones/mis-envios` que retorna las comunicaciones donde `enviado_por` coincide con el `usuario.id` del usuario autenticado (resuelto desde JWT mediante `resolve_domain_user_id`), scoped al `tenant_id` de la sesión. El endpoint SHALL requerir el permiso `comunicacion:enviar`. El endpoint SHALL soportar los query params opcionales `estado` (uno de: `Pendiente`, `Enviando`, `Enviado`, `Error`, `Cancelado`) y `offset` / `limit` (enteros, defaults `0` / `20`). La respuesta SHALL incluir `total` (conteo sin paginar), `offset`, `limit` y `items` (lista de `ComunicacionRead`).

#### Scenario: PROFESOR consulta su historial sin filtros
- **WHEN** un usuario con permiso `comunicacion:enviar` realiza `GET /comunicaciones/mis-envios` sin query params
- **THEN** el sistema responde 200 con `{"total": N, "offset": 0, "limit": 20, "items": [...]}`
- **AND** todos los items tienen `enviado_por` igual al `usuario.id` del usuario autenticado
- **AND** todos los items pertenecen al `tenant_id` de la sesión

#### Scenario: Filtro por estado retorna solo las comunicaciones en ese estado
- **WHEN** el usuario realiza `GET /comunicaciones/mis-envios?estado=Enviado`
- **THEN** todos los items en `items` tienen `estado == "Enviado"`
- **AND** el `total` refleja el conteo filtrado por ese estado

#### Scenario: Paginación con offset y limit
- **WHEN** el usuario realiza `GET /comunicaciones/mis-envios?offset=10&limit=5`
- **THEN** la respuesta contiene como máximo 5 items
- **AND** `offset` es 10 y `limit` es 5

#### Scenario: Usuario sin comunicaciones propias recibe lista vacía
- **WHEN** el usuario no ha enviado ninguna comunicación
- **THEN** el sistema responde 200 con `{"total": 0, "offset": 0, "limit": 20, "items": []}`

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin el permiso `comunicacion:enviar` realiza `GET /comunicaciones/mis-envios`
- **THEN** el sistema responde 403

#### Scenario: Aislamiento multi-tenant
- **WHEN** el usuario A del tenant T1 tiene comunicaciones propias
- **AND** el usuario B del tenant T2 realiza `GET /comunicaciones/mis-envios`
- **THEN** la respuesta de B NO contiene las comunicaciones del tenant T1

### Requirement: Método list_by_sender en ComunicacionRepository
El sistema SHALL proveer el método `list_by_sender(sender_id, estado?, offset, limit)` en `ComunicacionRepository` que filtra por `enviado_por == sender_id` AND `tenant_id == self._tenant_id` AND `deleted_at IS NULL`, con filtro adicional por `estado` si se provee, y aplica `OFFSET` / `LIMIT`. El método SHALL retornar una tupla `(items: List[Comunicacion], total: int)` donde `total` es el conteo sin paginar de los registros que satisfacen los filtros.

#### Scenario: list_by_sender retorna solo comunicaciones del remitente en el tenant
- **WHEN** se llama `list_by_sender(sender_id=X)` en el repositorio del tenant T
- **THEN** todos los registros retornados tienen `enviado_por == X` AND `tenant_id == T`
- **AND** los registros con `deleted_at IS NOT NULL` están excluidos

#### Scenario: list_by_sender con filtro de estado
- **WHEN** se llama `list_by_sender(sender_id=X, estado=ComunicacionEstado.Enviado)`
- **THEN** todos los registros retornados tienen `estado == Enviado`

#### Scenario: list_by_sender retorna total correcto con paginación
- **WHEN** existen 15 comunicaciones de sender X y se llama `list_by_sender(sender_id=X, offset=0, limit=5)`
- **THEN** `items` contiene 5 registros y `total` es 15

### Requirement: Índice de base de datos para la query de historial
El sistema SHALL tener un índice compuesto en `(tenant_id, enviado_por, created_at DESC)` sobre la tabla `comunicacion` para garantizar performance aceptable en la query de historial a medida que la tabla crece.

#### Scenario: El índice existe en la base de datos
- **WHEN** se ejecuta la migración Alembic de C-27
- **THEN** el índice `ix_comunicacion_tenant_enviado_por_created` existe en la tabla `comunicacion`
