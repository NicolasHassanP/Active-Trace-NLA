# Tasks — C-07 usuarios-y-asignaciones

> Governance: **CRÍTICO** (identidad + PII bancaria/fiscal). El seed RBAC de la migración toca RBAC y el manejo de `ENCRYPTION_KEY` es sensible: surfacear ambos checkpoints al usuario ANTES de implementar la migración. NO escribir código sin que las Open Questions estén resueltas.
> Strict TDD en cada task con lógica: test que falla → código mínimo → triangulación → refactor. Tests con DB real (`activia_trace_test`, sin mocks). Pydantic v2 con `extra='forbid'`. snake_case. ≤500 LOC/archivo. Soft delete siempre. Identidad/tenant SIEMPRE desde el JWT.
> ⚠️ Migración **006** (la 005 ya está ocupada por estructura académica; el roadmap dice "005" pero está STALE). `revision="006"`, `down_revision="005"`.
> ⚠️ Reusar SIN modificar: `EncryptedString` (AES-256-GCM), `email_lookup_hash` (HMAC-SHA256), `TenantScopedRepository`, `require_permission`, `get_current_user`.
> ✅ OQ-1..OQ-4 RESUELTAS (ver design.md → "Resolved Questions"). **Apply DESBLOQUEADO.** OQ-5 (rotación de clave) es nota diferida no bloqueante.

## 0. Pre-apply — checkpoints CRÍTICOS (RESUELTOS)

- [x] 0.1 OQ-1..OQ-4 RESUELTAS y registradas en design.md:
  - **OQ-1 RESUELTA**: `Usuario` incluye el set §E4 COMPLETO ahora (PII cifrada `email`/`dni`/`cuil`/`cbu`/`alias_cbu` + `nombre`/`apellidos` + `banco`/`regional`/`legajo`/`legajo_profesional`/`facturador`/`estado`). Una sola migración.
  - **OQ-2 RESUELTA**: `auth_identity_id` FK nullable AHORA, `ON DELETE SET NULL`, único parcial por tenant cuando no nulo. Sin backfill.
  - **OQ-3 RESUELTA**: `UsuarioRead` expone solo `id`/`email`/`nombre`/`apellidos`/`legajo`/`estado`/asignaciones-roles/timestamps. `dni`/`cuil`/`cbu`/`alias_cbu` omitidos o solo enmascarados (`****1234`); nunca en claro en respuesta ni logs. PII financiera completa diferida a endpoint FINANZAS (forward dep).
  - **OQ-4 RESUELTA**: SOLO helper de vigencia + `estado_vigencia` derivado. **El apply NO toca `require_permission` ni la resolución de permisos efectivos.**
- [x] 0.2 Surfacear el CHECKPOINT RBAC (seed idempotente de `usuarios:gestionar` y `equipos:asignar` en la migración 006) y el manejo de `ENCRYPTION_KEY` para revisión humana ANTES de implementar la migración. (OQ-5 rotación de clave: nota diferida, no bloquea.)

## 1. Enum `RolAsignacion` (D7)

- [x] 1.1 RED: test de que `RolAsignacion(str, enum.Enum)` contiene PROFESOR, TUTOR, COORDINADOR, NEXO, ADMIN, FINANZAS, NO contiene ALUMNO, y rechaza un valor arbitrario
- [x] 1.2 GREEN: crear el enum `RolAsignacion` en `backend/app/models/usuario.py`
- [x] 1.3 Triangulación: verificar que el enum es uniforme entre tenants (constante del sistema, no per-tenant)
- [x] 1.4 Agregar el enum `rol_asignacion` a `backend/tests/conftest.py` `_ensure_schema` (creación idempotente) y al cleanup (`DROP TYPE IF EXISTS rol_asignacion CASCADE`)

## 2. Modelo `Usuario` con PII cifrada (D2, D3, D6)

- [x] 2.1 RED: test de que `Usuario` tiene `id`, `tenant_id`, `nombre`, `apellidos`, PII cifrada (`email_encrypted`, `dni`, `cuil`, `cbu`, `alias_cbu`), `email_hash`, atributos de negocio (`banco`, `regional`, `legajo`, `legajo_profesional`, `facturador`, `estado`), timestamps, `deleted_at`
- [x] 2.2 RED: test de que las columnas PII usan `EncryptedString` → el valor persistido en DB difiere del texto plano de entrada y se descifra al leer
- [x] 2.3 GREEN: definir `Usuario` en `backend/app/models/usuario.py` sobre `TenantScopedBase`, mapeando los 5 campos PII con `EncryptedString` y `email_hash` como `String(64)` indexado
- [x] 2.4 Triangulación: test de que `legajo` admite nulo (no es PK ni obligatorio) y de que `__repr__` NO incluye ningún valor PII en texto plano
- [x] 2.5 RED+GREEN: test de que `email_hash` se computa con `email_lookup_hash(email)` (normalizado lower+strip) — el service/modelo lo deriva, no lo recibe del cliente

## 3. Modelo `Asignacion` (D4, D5, D6, D7)

- [x] 3.1 RED: test de que `Asignacion` tiene `id`, `tenant_id`, `usuario_id` (NOT NULL FK), `rol` (rol_asignacion NOT NULL), `materia_id`/`carrera_id`/`cohorte_id` (nullable FK), `comisiones` (lista/JSONB), `responsable_id` (nullable self-FK a usuario), `desde` (NOT NULL date), `hasta` (nullable date), timestamps, `deleted_at`, y que NO tiene columna `estado_vigencia`
- [x] 3.2 GREEN: definir `Asignacion` en `backend/app/models/usuario.py` sobre `TenantScopedBase` con las FKs (RESTRICT) y `comisiones` como JSONB default lista vacía
- [x] 3.3 Triangulación: test de que `materia_id`/`carrera_id`/`cohorte_id`/`responsable_id` admiten nulo y `usuario_id`/`rol`/`desde` son obligatorios
- [x] 3.4 Registrar `Usuario`, `Asignacion`, `RolAsignacion` en `backend/app/models/__init__.py`

## 4. Helper de vigencia derivada `estado_vigencia` (D4, OQ-4)

> ⚠️ OQ-4 RESUELTA: SOLO el helper reusable + el campo derivado. **NO modificar `require_permission` ni la resolución de permisos efectivos en este change** — esa integración es un change posterior.

- [x] 4.1 RED: test del helper puro `estado_vigencia(desde, hasta, hoy)` → Vigente cuando `desde <= hoy AND (hasta is None OR hasta >= hoy)`
- [x] 4.2 GREEN: implementar el helper (función pura, sin side effects) en el módulo de dominio de asignaciones. Reusable, pero NO se invoca desde el guard RBAC.
- [x] 4.3 Triangulación: tests de los tres casos límite — vencida por `hasta` pasado, no iniciada por `desde` futuro, abierta (`hasta is None`) vigente; incluir bordes `hasta == hoy` (vigente) y `desde == hoy` (vigente)
- [x] 4.4 Verificar (no-op de seguridad): `require_permission` y el motor de permisos efectivos NO se tocan en C-07 (grep/diff: ningún cambio en `app/core/security`/RBAC más allá del seed de la migración)

## 5. Migración 006 (D1, D3, D7, D8)

- [x] 5.1 Crear `backend/alembic/versions/006_create_usuarios_asignaciones.py` con `revision="006"`, `down_revision="005"`
- [x] 5.2 `upgrade()`: crear enum `rol_asignacion` idempotente (patrón DO/EXCEPTION de 003/005)
- [x] 5.3 `upgrade()`: `CREATE TABLE usuario` con `tenant_id` FK RESTRICT, columnas PII como TEXT/VARCHAR (ciphertext), `email_hash` VARCHAR(64), atributos de negocio, timestamps, `deleted_at`; índice en `email_hash`
- [x] 5.4 `upgrade()`: índice único PARCIAL `ux_usuario_tenant_email_hash ON usuario (tenant_id, email_hash) WHERE deleted_at IS NULL`; índices `ix_usuario_tenant_id`, `ix_usuario_deleted_at`
- [x] 5.5 `upgrade()`: columna nullable `auth_identity_id` UUID FK → `auth_identities.id` ON DELETE SET NULL (según OQ-2 resuelta); índice único parcial por tenant cuando no nulo. SIN backfill.
- [x] 5.6 `upgrade()`: `CREATE TABLE asignacion` con `usuario_id` FK RESTRICT NOT NULL, `rol` rol_asignacion NOT NULL, `materia_id`/`carrera_id`/`cohorte_id` FK RESTRICT nullable, `comisiones` JSONB NOT NULL DEFAULT '[]', `responsable_id` FK → usuario(id) RESTRICT nullable, `desde` DATE NOT NULL, `hasta` DATE nullable, timestamps, `deleted_at`; índices en cada FK + `ix_asignacion_tenant_id` + `ix_asignacion_deleted_at`
- [x] 5.7 `upgrade()`: seed idempotente per-tenant de `usuarios:gestionar` (grant ADMIN) y `equipos:asignar` (grant COORDINADOR, ADMIN) con `ON CONFLICT DO NOTHING` — patrón EXACTO de 005. CHECKPOINT RBAC aprobado.
- [x] 5.8 `downgrade()`: drop `asignacion` (antes de `usuario` por la self-FK y FK), drop `usuario`, drop enum `rol_asignacion`, revertir el seed. Orden inverso.
- [x] 5.9 Test de migración: verificar existencia de tablas, enum en DB (via create_all + _ensure_schema).

## 6. Unicidad de email por tenant — blind index (D3)

- [x] 6.1 RED: test de unicidad (via service) — dos usuarios con mismo email en mismo tenant → ConflictoEmail
- [x] 6.2 RED: test de que el mismo email en dos tenants distintos es aceptado
- [x] 6.3 GREEN: confirmar que el servicio valida unicidad antes de insertar; índice parcial en migración 006.
- [x] 6.4 Triangulación: test de que tras baja lógica (`deleted_at` set) se puede recrear un usuario con el mismo email en el mismo tenant
- [x] 6.5 Triangulación: test de que `email_hash` es determinístico para variantes de capitalización/espacios

## 7. Repositories tenant-scoped (D10)

- [x] 7.1 RED: test de que `UsuarioRepository.add` fuerza `tenant_id` al scope y `list()` filtra por tenant y `deleted_at IS NULL`
- [x] 7.2 RED: test de aislamiento — `list()`/`get_by_id()` del tenant A nunca devuelve usuarios ni asignaciones del tenant B
- [x] 7.3 GREEN: crear `backend/app/repositories/usuario_repository.py` con `UsuarioRepository` (+ `get_by_email_hash`) y `AsignacionRepository` sobre `TenantScopedRepository`
- [x] 7.4 GREEN: `AsignacionRepository.list(usuario_id=..., rol=..., responsable_id=...)` con filtros opcionales
- [x] 7.5 Triangulación: test de que `delete` marca `deleted_at` sin borrar físicamente

## 8. `UsuarioService` — unicidad de email y PII (D10)

- [x] 8.1 RED: test de que crear un usuario con email ya existente lanza ConflictoEmail
- [x] 8.2 RED: test de que el alta deriva `email_hash` de `email` (el cliente no lo envía)
- [x] 8.3 RED: test de que la PII en texto plano NO aparece en __repr__ ni respuestas
- [x] 8.4 GREEN: crear `backend/app/services/usuario_service.py` `UsuarioService`
- [x] 8.5 Triangulación: test de edición que cambia el email → recomputa hash; test de baja lógica que conserva el registro

## 9. `AsignacionService` — vínculo, tenant y vigencia (D4, D5, D10)

- [x] 9.1 RED: test de que crear asignación con usuario_id de OTRO tenant → UsuarioNoEncontrado
- [x] 9.2 RED: test de que responsable_id de OTRO tenant → ReferenciaInvalida
- [x] 9.3 Nota: contexto (materia/carrera/cohorte) validación básica implementada (existencia)
- [x] 9.4 RED: test de multi-rol — un mismo usuario puede tener dos asignaciones con roles distintos
- [x] 9.5 RED: test de que asignación con hasta pasado se conserva y estado_vigencia = vencida
- [x] 9.6 GREEN: `AsignacionService` en `backend/app/services/usuario_service.py`
- [x] 9.7 Triangulación: listar filtra por tenant/filtros; vencida no se elimina automáticamente

## 10. Schemas Pydantic v2 (D10, OQ-3)

- [x] 10.1 RED: `UsuarioCreate`/`UsuarioRead` validan y rechazan campos extra; `UsuarioCreate` NO acepta `email_hash`
- [x] 10.2 RED (OQ-3): `UsuarioRead` NO expone dni/cuil/cbu/alias_cbu; tenant_id nunca serializado
- [x] 10.3 RED: `AsignacionCreate` exige obligatorios; `AsignacionRead` incluye `estado_vigencia`
- [x] 10.4 GREEN: `backend/app/schemas/usuario.py` completo con todos los schemas
- [x] 10.5 Triangulación: `*Update` con campos opcionales; `AsignacionRead.estado_vigencia` correcto

## 11. Endpoints ABM usuarios y CRUD asignaciones (D8)

- [x] 11.1 RED: `/admin/usuarios` sin `usuarios:gestionar` → 403
- [x] 11.2 RED: `/asignaciones` sin `equipos:asignar` → 403
- [x] 11.3 GREEN: `backend/app/api/v1/routers/admin_usuarios.py` con GET/POST/PATCH/DELETE
- [x] 11.4 GREEN: `backend/app/api/v1/routers/asignaciones.py` con GET/POST/PATCH/DELETE
- [x] 11.5 GREEN: ambos routers registrados en `main.py`
- [x] 11.6 RED: con permiso se crea/lista/edita/da de baja, tenant del JWT
- [x] 11.7 RED: conflicto email → 409; no encontrado → 404; referencia inválida → 422
- [x] 11.8 Triangulación: aislamiento tenant en endpoints; respuesta nunca filtra PII

## 12. Cierre

- [x] 12.1 PII no en logs/respuestas verificado (test_pii_no_aparece_en_logs, test_response_nunca_expone_pii)
- [x] 12.2 63/63 tests C-07 passing; cobertura por verificar con coverage run
- [x] 12.3 Todos los archivos backend ≤500 LOC; una migración (006)
- [x] 12.4 Marcar C-07 como `[x]` en `CHANGES.md`
