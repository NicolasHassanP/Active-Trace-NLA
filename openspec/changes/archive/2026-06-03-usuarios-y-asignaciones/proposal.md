## Why

Tras C-06 el sistema tiene el catálogo estructural (Carrera, Cohorte, Materia) pero no tiene **identidad de negocio completa** ni el **eje de autorización contextual**. C-03 entregó `AuthIdentity` (subconjunto mínimo para autenticar) explícitamente diseñado para ser reconciliado por `Usuario` en C-07. Sin `Usuario` y `Asignacion` no se puede modelar quién es cada persona (con su PII bancaria/fiscal cifrada), ni vincularla a un rol dentro de un contexto académico con vigencia temporal — el prerequisito de todos los módulos académicos posteriores (C-08 equipos, C-09 padrón, C-13 encuentros, C-14 coloquios, etc., que cuelgan de `Asignacion`).

C-07 es el **FORK ANCHO** del roadmap (GATE 6): cerrarlo desbloquea 8 changes en paralelo.

## What Changes

- **Nuevo modelo `Usuario`** (identidad de negocio del tenant): set §E4 COMPLETO en una sola migración — `nombre`, `apellidos`, PII **cifrada en reposo AES-256** (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`), más atributos de negocio (`banco`, `regional`, `legajo`, `legajo_profesional`, `facturador`, `estado`), y **FK nullable `auth_identity_id`** (→ `auth_identities`, `ON DELETE SET NULL`) que deja listo el gancho de reconciliación con la credencial de C-03 (sin backfill en C-07). `legajo` es atributo de negocio opcional — NUNCA PK ni credencial (regla dura #14).
- **Nuevo modelo `Asignacion`** (Usuario ↔ Rol ↔ contexto académico): `usuario_id`, `rol`, `materia_id`/`carrera_id`/`cohorte_id` (nullable), `comisiones` (lista), `responsable_id` (jerarquía, self-FK a Usuario), ventana de vigencia `desde`/`hasta`, y `estado_vigencia` **derivado** (no almacenado).
- **Unicidad `(tenant_id, email)`** sobre email cifrado, vía **blind index** determinístico (`email_hash` HMAC-SHA256) — reusa el patrón ya establecido en `AuthIdentity`.
- **ABM de usuarios** bajo `/api/v1/admin/usuarios`, protegido por `usuarios:gestionar` (ADMIN), fail-closed.
- **CRUD de asignaciones** bajo `/api/v1/asignaciones`, protegido por `equipos:asignar` (COORDINADOR, ADMIN), fail-closed.
- **Regla de vigencia**: una asignación VENCIDA no otorga permisos pero se CONSERVA (histórico append-only). `estado_vigencia` se computa de `desde`/`hasta` vs fecha actual. C-07 entrega SOLO el helper de vigencia + el campo derivado; **NO** integra la vigencia en `require_permission` (eso es un change posterior).
- **Exposición de PII**: `UsuarioRead` (ABM general) expone email/nombre/legajo/estado/roles/timestamps; la PII financiera (`dni`/`cuil`/`cbu`/`alias_cbu`) queda omitida o enmascarada — su lectura completa se difiere a un endpoint FINANZAS posterior (dependencia forward).
- **Migración 006** `006_create_usuarios_asignaciones.py`: tablas `usuario` y `asignacion` + enum `rol_asignacion`. (Los permisos `usuarios:gestionar` y `equipos:asignar` YA están sembrados desde la migración 003 — el seed idempotente solo cubre tenants creados después.)

**BREAKING**: ninguno externo. Internamente, `Usuario` reconcilia el rol que cumplía `AuthIdentity` (ver design.md, decisión sobre `auth_identity_id`).

## Capabilities

### New Capabilities
- `usuarios`: identidad de negocio del tenant con PII cifrada en reposo (AES-256), unicidad de email por tenant vía blind index, ABM ADMIN-only, sin exposición de PII en logs ni respuestas más allá del contrato del endpoint.
- `asignaciones`: vínculo Usuario ↔ Rol ↔ contexto académico con vigencia temporal, jerarquía de responsable, multi-rol, y derivación de `estado_vigencia`; una asignación vencida no autoriza pero se conserva.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus REQUISITOS a nivel spec. C-07 solo
     consume el mecanismo RBAC ya entregado por C-04 (no lo modifica) y reusa los
     helpers de cifrado de C-02/C-03. -->

## Impact

- **Modelos**: nuevo `backend/app/models/usuario.py` (Usuario, Asignacion, enum RolAsignacion).
- **Migración**: nueva `backend/alembic/versions/006_create_usuarios_asignaciones.py` (`revision="006"`, `down_revision="005"`).
- **Repositories**: nuevo `backend/app/repositories/usuario_repository.py` (UsuarioRepository, AsignacionRepository).
- **Services**: nuevo `backend/app/services/usuario_service.py` (UsuarioService, AsignacionService) con la lógica de unicidad, vigencia y jerarquía.
- **Schemas**: nuevo `backend/app/schemas/usuario.py` (Usuario/Asignacion Create/Update/Read).
- **Routers**: nuevos `backend/app/api/v1/routers/admin_usuarios.py` y `asignaciones.py`, registrados en el agregador v1.
- **Reusa sin modificar**: `app.core.security.EncryptedString` (AES-256-GCM), `app.core.security.email_lookup_hash` (HMAC-SHA256), `TenantScopedRepository`, `require_permission`, `get_current_user`.
- **Tests**: nuevos tests en `backend/tests/`; alta del enum `rol_asignacion` en `conftest.py` `_ensure_schema` + drop en cleanup.
- **Governance**: CRÍTICO (identidad + PII). Las Open Questions de seguridad OQ-1..OQ-4 están RESUELTAS y bloqueadas en design.md (apply DESBLOQUEADO); persiste el checkpoint humano del seed RBAC y el manejo de `ENCRYPTION_KEY` antes de aplicar la migración. OQ-5 (rotación de clave) queda diferida, no bloquea.
