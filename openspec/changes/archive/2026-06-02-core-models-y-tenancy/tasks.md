## 1. Preparación y dependencias

- [x] 1.1 Confirmar el baseline: correr la suite de tests de C-01 (`pytest`) y registrar "N tests passing"; no continuar si hay fallos pre-existentes (reportar al orquestador)
- [x] 1.2 Agregar la dependencia de criptografía (`cryptography`) al `backend/pyproject.toml`; no tocar el resto del stack ya declarado por C-01
- [x] 1.3 Verificar que `tests/conftest.py` tiene una fixture de sesión de DB de test efímera (PostgreSQL real / asyncpg) y de creación/teardown de tablas; extenderla si hace falta para los modelos de C-02 (sin mockear la DB)

## 2. Cifrado AES-256 (core/security.py)

- [x] 2.1 (RED) Escribir `tests/test_security_encryption.py`: test que cifra un valor y al descifrarlo recupera el original (`decrypt(encrypt(x)) == x`), usando `ENCRYPTION_KEY` de `Settings`
- [x] 2.2 (GREEN) Implementar en `core/security.py` los helpers `encrypt(plaintext: str) -> str` y `decrypt(ciphertext: str) -> str` con **`AESGCM` de `cryptography.hazmat.primitives.ciphers.aead`**, clave de 32 bytes desde `ENCRYPTION_KEY`, nonce de 12 bytes aleatorio por operación, salida `nonce || ciphertext` codificada (base64 urlsafe). NO usar Fernet (es AES-128)
- [x] 2.3 (TRIANGULATE) Agregar casos: cadena vacía, unicode, valor largo; verificar además que el ciphertext difiere del texto plano y que un ciphertext manipulado falla al descifrar
- [x] 2.4 (RED) Escribir test del `TypeDecorator` de columna: una entidad de prueba con un campo cifrado, al persistir y releer devuelve el texto plano, pero el valor crudo en la columna está cifrado
- [x] 2.5 (GREEN) Implementar el `TypeDecorator` `EncryptedString` en `core/security.py` (`process_bind_param` cifra, `process_result_value` descifra) sobre los helpers anteriores
- [x] 2.6 (TRIANGULATE) Verificar round-trip transparente con varios valores y que el `__repr__`/logging de un modelo con campo cifrado NO expone el texto plano
- [x] 2.7 (REFACTOR) Extraer constantes/derivación de clave, mejorar nombres; correr tests tras cada cambio → verde

## 3. Mixin base de persistencia (models/mixins.py)

- [x] 3.1 (RED) Escribir `tests/test_mixins.py`: con una entidad de prueba que use el mixin, al crear se setean `id` (UUID), `created_at` y `updated_at`, y `deleted_at` es nulo
- [x] 3.2 (GREEN) Implementar en `models/mixins.py` los mixins combinables: `UUIDMixin` (`id` UUID PK, default uuid4), `TimestampMixin` (`created_at`, `updated_at` con `onupdate`), `SoftDeleteMixin` (`deleted_at` nullable), `TenantMixin` (`tenant_id` UUID FK→`tenants.id`, no nulo, indexado)
- [x] 3.3 (GREEN) Definir el alias de conveniencia `TenantScopedBase` que agrupa `UUIDMixin + TenantMixin + TimestampMixin + SoftDeleteMixin` para que las entidades de negocio hereden de una sola clase
- [x] 3.4 (TRIANGULATE) Agregar caso: al modificar y persistir la entidad, `updated_at` cambia y `created_at` no; verificar que una entidad de negocio (con `TenantMixin`) sí lleva `tenant_id` no nulo
- [x] 3.5 (REFACTOR) Limpiar duplicación entre mixins; tests verdes tras cada paso

## 4. Modelo Tenant (models/tenant.py)

- [x] 4.1 (RED) Escribir `tests/test_tenant_model.py`: crear un `Tenant` con nombre y estado válidos lo persiste con `id` UUID y timestamps; verificar que la tabla `tenants` NO tiene columna `tenant_id`
- [x] 4.2 (GREEN) Implementar `models/tenant.py`: `Tenant` = `Base + UUIDMixin + TimestampMixin + SoftDeleteMixin` (sin `TenantMixin`, es la raíz), con `nombre` y `estado` (enum Activo/Inactivo)
- [x] 4.3 (TRIANGULATE) Agregar caso: una segunda entidad de negocio de prueba que herede de `TenantScopedBase` y referencie a `tenants.id` por `tenant_id`, confirmando la asimetría raíz vs. entidad de negocio

## 5. Migración Alembic 001 (tenant)

- [x] 5.1 Asegurar que `alembic/env.py` importa los modelos de C-02 (vía `Base.metadata`) para que el esquema sea visible al generar
- [x] 5.2 Crear la migración `alembic/versions/001_*.py` (autogenerada como borrador y revisada a mano) que crea la tabla `tenants` con sus columnas (`id`, `nombre`, `estado`, `created_at`, `updated_at`, `deleted_at`) e índices
- [x] 5.3 Verificar `alembic upgrade head` (crea `tenants`) y `alembic downgrade -1` (la elimina) contra la DB de test, dejando el esquema consistente

## 6. Repository genérico tenant-scoped (repositories/base.py)

- [x] 6.1 (RED) Escribir `tests/test_tenant_scoped_repository.py`: con datos de los tenants A y B, un repository scoped a A lista sólo registros de A y ninguno de B
- [x] 6.2 (GREEN) Implementar `TenantScopedRepository[ModelT]` en `repositories/base.py`: se construye con `(session, tenant_id)`, guarda el `tenant_id` como estado, y `list`/`get_by_id` filtran por ese `tenant_id` automáticamente
- [x] 6.3 (TRIANGULATE) Agregar caso: `get_by_id` de un registro del tenant B desde un repository scoped a A devuelve `None` (aislamiento por id)
- [x] 6.4 (RED) Escribir test de creación: crear una entidad vía un repository scoped a A fija `tenant_id = A` aunque se pase otro `tenant_id`
- [x] 6.5 (GREEN) Implementar `add`/`create` en el repository: fija `tenant_id` desde el scope, ignorando cualquier valor entrante; persiste y refresca
- [x] 6.6 (TRIANGULATE) Verificar que ningún método de lectura del repository acepta `tenant_id` como parámetro (el scope sólo se inyecta en construcción)
- [x] 6.7 (REFACTOR) Extraer el armado del `WHERE tenant_id = ...` a un helper reutilizable; tests verdes tras cada paso
- [x] 6.8 `core/tenancy.py`: dejar SOLO el contrato de inyección del scope de tenant en el repository (desacoplado de auth). NO implementar `get_tenant` ni nada que lea el JWT/sesión — eso se posterga a C-03. Mantener el docstring de reserva si no hay contrato concreto que ubicar acá

## 7. Soft delete transversal (en el repository)

- [x] 7.1 (RED) Escribir test de soft delete: tras `delete()`, el registro no aparece en `list()` por defecto, pero la fila sigue físicamente en la tabla (consulta cruda)
- [x] 7.2 (GREEN) Implementar `delete(obj)` en el repository como marcado de `deleted_at` (nunca `DELETE` físico) y el filtro por defecto `deleted_at IS NULL` en las lecturas
- [x] 7.3 (TRIANGULATE) Agregar caso: `list(include_deleted=True)` incluye el registro borrado; verificar que sin el flag no aparece
- [x] 7.4 (REFACTOR) Consolidar el filtro de soft delete junto al de tenant en el helper de lectura; tests verdes

## 8. Verificación final

- [x] 8.1 Correr la suite completa (`pytest`) y confirmar verde: cifrado round-trip, mixin/timestamps, modelo Tenant, repository tenant-scoped, aislamiento multi-tenant, soft delete
- [x] 8.2 Confirmar cobertura ≥80% líneas y ≥90% en las reglas de negocio de este change (aislamiento, soft delete, cifrado)
- [x] 8.3 Confirmar que ningún archivo backend nuevo supera 500 LOC y que el árbol respeta `docs/ARQUITECTURA.md §4` (`models/`, `repositories/`, `core/security.py`)
- [x] 8.4 Revisar que ningún test mockea la base de datos y que ningún query del repository queda sin scope de tenant
