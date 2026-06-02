# Arquitectura — activia-trace

**Producto**: activia-trace
**Versión del documento**: 0.3
**Fecha**: 2026-05-28
**Estado**: Draft — arquitectura objetivo (target), aún sin implementación
**Referencias**: [PRD](./PRD.md) · [Arquitectura (resumen en la KB)](../knowledge-base/08_arquitectura_propuesta.md) · [Modelo de datos](../knowledge-base/04_modelo_de_datos.md)

---

## 1. Propósito y filosofía

activia-trace es una plataforma de gestión académica y trazabilidad de actividades estudiantiles, diseñada para integrarse con **Moodle** como LMS y operar de forma multi-tenant desde el origen. Las decisiones de arquitectura responden directamente a los requisitos del producto.

**Principios rectores:**

1. **CONCEPTOS > CÓDIGO** — la arquitectura se diseña antes de tipear. Este documento es el contrato.
2. **Separación estricta de capas** — la lógica de negocio nunca toca HTTP ni SQL directamente.
3. **La identidad jamás se deriva de un parámetro de request** — el usuario y el tenant se resuelven exclusivamente desde la sesión autenticada (JWT verificado).
4. **Multi-tenant desde el día 0** — no es un retrofit; es la raíz del modelo.
5. **Todo audita** — el nombre del producto es *trace*. Cada acción significativa queda atribuida a un actor real, en un tenant, con timestamp.

---

## 2. Stack tecnológico

El stack es una decisión propia del producto, seleccionado por idoneidad técnica para los requisitos de seguridad, rendimiento y mantenibilidad.

### Backend

| Componente | Tecnología | Notas |
|------------|-----------|-------|
| Lenguaje | **Python 3.13** | |
| Framework | **FastAPI** | API REST async |
| ORM | **SQLAlchemy 2.0** (async) | Mapeo + queries en repositories |
| Migraciones | **Alembic** | Una migración por cambio de schema |
| Base de datos | **PostgreSQL** | JSONB para criterios/scores configurables |
| Validación | **Pydantic v2** | DTOs request/response (schemas) |
| Auth | **JWT** (access corto + refresh rotation) + **Argon2id** para hashing de passwords | |
| Cifrado en reposo | **AES-256** | Para PII sensible (CBU, DNI) y secretos |
| Background jobs | **Worker async** (cola de comunicaciones) | Estados Pend → Send → OK/Fail y Pend → Canc |
| Integraciones | **N8N** + **Moodle Web Services** | Cliente dedicado `moodle_ws.py` |
| Testing | **pytest** + coverage | ≥80% líneas, ≥90% reglas de negocio ([RNF-15](./PRD.md#mantenibilidad)) |

### Frontend

| Componente | Tecnología | Notas |
|------------|-----------|-------|
| Framework | **React 18** + **TypeScript** | Sin `any`, sin class components |
| Bundler | **Vite** | HMR en dev |
| Server state | **React Query (TanStack Query)** | Todo fetch pasa por hooks de `services/` |
| Forms | **React Hook Form + Zod** | Validación tipada |
| Estilos | **Tailwind CSS** | Sin CSS modules, sin inline (salvo valores dinámicos) |
| HTTP | **Axios** | Cliente centralizado en `@/shared/services/api` |
| Estructura | **Feature-based modules** | `features/{name}/{components,hooks,services,types,pages}` |

### Infraestructura

| Componente | Tecnología |
|------------|-----------|
| Contenedores | **Docker** + docker-compose (local y prod) |
| Deploy | **Easypanel** |
| Observabilidad | Logs estructurados JSON + **OpenTelemetry** ([RNF-17](./PRD.md#mantenibilidad)) |
| CI/CD | build + test + lint + deploy automatizado ([RNF-16](./PRD.md#mantenibilidad)) |

---

## 3. Arquitectura backend — Clean Architecture

El flujo de una request es **unidireccional** y cada capa tiene una sola responsabilidad:

```
REQUEST
   │
   ▼
┌──────────────┐  HTTP, validación Pydantic, auth/authz. NADA de lógica de negocio.
│   Routers    │
└──────┬───────┘
       ▼
┌──────────────┐  Lógica de negocio. NO accede a la DB directamente.
│   Services   │
└──────┬───────┘
       ▼
┌──────────────┐  TODAS las queries SQLAlchemy. NADA de reglas de negocio.
│ Repositories │
└──────┬───────┘
       ▼
┌──────────────┐  Entidades ORM (SQLAlchemy).
│    Models    │
└──────┬───────┘
       ▼
   PostgreSQL
```

**Reglas no negociables:**

- **Nunca** lógica de negocio en Routers.
- **Nunca** acceso directo a DB desde Services (siempre vía Repository).
- Secretos (API keys, tokens externos) **siempre** AES-256 — jamás en texto plano.
- **Soft delete** siempre (audit). Nunca hard delete.
- Validar permisos por rol **en cada endpoint** — y además scope por tenant (ver §6).
- Máximo **500 LOC por archivo** backend.
- Manejo de errores estandarizado:

  | Tipo | Respuesta |
  |------|-----------|
  | Validación | `HTTPException 400` |
  | No autenticado | `HTTPException 401` |
  | Sin permiso (authz) | `HTTPException 403` |
  | No encontrado | `HTTPException 404` |
  | Error de integración externa | `HTTPException 502` + retry |
  | Interno | `HTTPException 500` + log detallado |

---

## 4. Estructura de directorios

### Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py                  # Bootstrap FastAPI
│   ├── api/v1/routers/          # Routers por dominio
│   ├── core/
│   │   ├── config.py            # Settings (env vars)
│   │   ├── security.py          # JWT, Argon2, AES-256
│   │   ├── permissions.py       # RBAC: matriz rol × permiso
│   │   ├── tenancy.py           # Resolución y aislamiento de tenant
│   │   ├── dependencies.py      # DI: get_current_user, get_tenant, require_permission
│   │   └── exceptions.py
│   ├── models/                  # SQLAlchemy ORM
│   ├── schemas/                 # Pydantic DTOs
│   ├── repositories/            # Queries (tenant-scoped por defecto)
│   ├── services/                # Lógica de negocio
│   ├── integrations/
│   │   ├── n8n_client.py
│   │   └── moodle_ws.py         # Cliente Moodle Web Services
│   └── workers/                 # Worker de cola de comunicaciones
├── alembic/                     # Migraciones
└── tests/
```

### Frontend (`frontend/`)

```
frontend/src/
├── features/
│   └── {dominio}/               # auth, alumnos, materias, comisiones,
│       ├── components/          #   atrasados, comunicacion, equipos,
│       ├── hooks/               #   encuentros, coloquios, liquidaciones,
│       ├── services/            #   auditoria, perfil
│       ├── types/
│       └── pages/
└── shared/
    ├── services/api.ts          # Axios centralizado + interceptor JWT/refresh
    ├── components/              # UI reutilizable
    └── hooks/
```

---

## 5. Modelo de seguridad

### 5.1 Autenticación

- Login con **email + password** ([RF-01](./PRD.md#auth-roles-y-tenants)). Password hasheado con **Argon2id** (nunca MD5/SHA simple, nunca texto plano).
- **2FA opcional (TOTP)** por usuario.
- Recuperación de contraseña por email con token de un solo uso y expiración corta ([RF-02](./PRD.md#auth-roles-y-tenants)).
- Sesión = **JWT firmado**, access token de vida corta (**15 min**, [RNF-09](./PRD.md#seguridad)) + **refresh token con rotación** (un refresh usado se invalida).
- El JWT lleva claims mínimos: `sub` (user id), `tenant_id`, `roles`, `exp`. **Nada de permisos en el token** — se resuelven server-side.

### 5.2 Autorización (RBAC)

- Roles del dominio ([RF-04](./PRD.md#auth-roles-y-tenants)): **ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS**.
- **Permisos finos por feature**, no por rol monolítico. Matriz rol × permiso en `core/permissions.py`.
- Cada endpoint declara el permiso requerido vía dependency (`require_permission("entregas:write")`). Sin él → `403`.

### 5.3 Principios de control de acceso

El control de acceso de activia-trace se rige por los siguientes principios, que son invariantes del sistema:

| Principio | Descripción |
|-----------|-------------|
| **Identidad desde la sesión** | El usuario y el tenant se derivan **exclusivamente** del JWT verificado server-side. Ningún parámetro de query string, body ni header puede alterar o reemplazar la identidad del actor. Cualquier identificador que llegue en la request se trata como dato de entrada a validar contra los permisos del usuario actual, nunca como su identidad. |
| **RBAC fino y explícito** | La autorización se resuelve en cada endpoint a partir de la matriz rol × permiso. No existe un flag binario de "super usuario": las capacidades se otorgan permiso a permiso. |
| **Impersonation permisada y auditada** | La impersonación legítima (soporte / administración) es una feature explícita: requiere el permiso `impersonation:use`, genera un token de impersonation distinguible y registra en el audit log quién impersona a quién, desde cuándo y hasta cuándo ([RF-05](./PRD.md#auth-roles-y-tenants), [RNF-12](./PRD.md#seguridad)). Toda acción bajo impersonation queda atribuida al actor real, no al usuario impersonado. |
| **Aislamiento de tenant** | Los repositories filtran por `tenant_id` por defecto. Un query sin scope de tenant es un bug que debe fallar en code review. Los datos nunca cruzan tenants. |
| **Fail-closed** | Ante cualquier ambigüedad de permisos, el sistema deniega. |

### 5.4 Otras defensas transversales

- **HTTPS/TLS 1.3** en todo el tráfico ([RNF-07](./PRD.md#seguridad)).
- **PII cifrada en reposo** (CBU, DNI) con AES-256 ([RNF-08](./PRD.md#seguridad)).
- **CSRF protection** en endpoints state-changing ([RNF-10](./PRD.md#seguridad)).
- **Rate limiting** por IP y por usuario ([RNF-11](./PRD.md#seguridad)).
- **Audit log append-only** (idealmente write-once), sin límite de retención ([RNF-12](./PRD.md#seguridad), [RF-38](./PRD.md#auditoría)).

---

## 6. Multi-tenancy

Multi-tenancy es nativo en activia-trace desde el día 0 ([RF-03](./PRD.md#auth-roles-y-tenants), [RNF-22](./PRD.md#multi-tenancy)).

- **Tenant** es el primer nivel del modelo: una institución = un tenant.
- **Estrategia (ADR-002, cerrada — ver §10)**: **row-level** — columna `tenant_id` en toda tabla + filtro automático en cada repository. Una sola base de datos. Database-per-tenant se reevaluará solo si un tenant exige aislamiento físico regulatorio.
- El `tenant_id` se resuelve del JWT (§5.1) y se inyecta vía dependency. **Los repositories filtran por tenant por defecto** — un query sin scope de tenant es un bug que debe fallar en code review.
- **Los datos jamás cruzan tenants.** Test obligatorio: un usuario del tenant A nunca puede leer/escribir datos del tenant B.
- Configuración por tenant ([RNF-23](./PRD.md#multi-tenancy)): idioma, branding, plantillas de mail, catálogo de escalas textuales, flag de aprobación de mails.

---

## 7. Integraciones

### 7.1 Moodle Web Services

activia-trace se integra con **Moodle** (el LMS) a través de su API de Web Services ([RF-06](./PRD.md#ingesta-y-datos)):

- **Funciones utilizadas**: `core_grades_get_grades`, `core_enrol_get_enrolled_users`, `core_user_get_users`, `gradereport_user_get_grade_items`, entre otras según la versión de Moodle del tenant.
- **Sync nocturna automática** + sync on-demand desde la interfaz.
- La columna `(Real)` en los reportes de calificaciones refleja el dato importado directamente desde Moodle, sin transformación.
- El snippet HTML de Moodle SSO (embedding en páginas de Moodle) usa el token de sesión para identificar al usuario sin re-login.
- **Fallback**: import manual `.xlsx`/`.csv` para tenants sin acceso a Moodle Web Services, o para carga inicial de datos históricos ([RF-07](./PRD.md#ingesta-y-datos)).
- Cliente aislado en `integrations/moodle_ws.py`; los errores mapean a `502 + retry`.
- Variables de entorno por tenant: `MOODLE_WS_TOKEN`, `MOODLE_WS_URL` (ver §9).
- El scope de commits para esta integración es `moodle`.

### 7.2 Cola de comunicaciones (worker async)

- Ciclo de vida de mensajes con estados **Pend → Send → OK/Fail** y **Pend → Canc** ([RF-18](./PRD.md#comunicación)).
- **Preview obligatorio** antes de encolar ([RF-17](./PRD.md#comunicación)).
- **Aprobación humana opcional por tenant** ([RF-19](./PRD.md#comunicación)).
- Plantillas con variables `{{alumno.nombre}}`, `{{materia.nombre}}` ([RF-20](./PRD.md#comunicación)).

### 7.3 N8N

- Orquestación de flujos externos. Se evalúa si activia-trace lo necesita en MVP o si el worker propio alcanza (ADR-003).

---

## 8. Persistencia y modelo de datos

- PostgreSQL. Modelo detallado en [`knowledge-base/04`](../knowledge-base/04_modelo_de_datos.md).
- **JSONB** para estructuras configurables (criterios, escalas, scores).
- Decisiones estructurales clave del modelo:
  - `Tenant` como raíz de toda entidad.
  - **Padrón con historial** (versionado, no upsert destructivo — [RF-08](./PRD.md#ingesta-y-datos)).
  - **Catálogo único de materias** por tenant ([RF-09](./PRD.md#ingesta-y-datos)).
  - Audit log append-only sin límite de registros.
- **Identidad de usuario**: la identificación interna es un **UUID**, que es el único selector válido para autenticación y autorización. El número de legajo, cuando existe, es un **atributo de negocio** (visible en pantallas, buscable) pero nunca actúa como credencial, como PK de identidad ni como parámetro de sesión.

---

## 9. Convenciones

### Commits (Conventional Commits)

`<type>(<scope>): <descripción>`

- **Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- **Scopes**: `auth`, `tenancy`, `users`, `alumnos`, `materias`, `comisiones`, `entregas`, `comunicacion`, `equipos`, `encuentros`, `coloquios`, `liquidaciones`, `auditoria`, `moodle`, `api`, `ui`

### Código

- Backend: Clean Architecture estricta (§3), ≤500 LOC/archivo.
- Frontend: componentes funcionales TS, <200 LOC, pages lazy-loaded, loading + error states siempre.

### Variables de entorno clave

| Variable | Propósito |
|----------|-----------|
| `DATABASE_URL` | Conexión PostgreSQL |
| `SECRET_KEY` | Firma JWT (mín. 32 chars) |
| `ENCRYPTION_KEY` | AES-256 para PII/secretos (exactamente 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración access token (default 15) |
| `MOODLE_WS_TOKEN` | Token de acceso a Moodle Web Services (por tenant) |
| `MOODLE_WS_URL` | URL base de la instancia Moodle (por tenant) |
| `N8N_WEBHOOK_URL` | Servicio N8N |

---

## 10. Decisiones de arquitectura (ADRs)

### Decisiones de cimiento — CERRADAS (definidas antes de codear)

Estas tres decisiones tocan transversalmente el sistema (cada tabla, cada request, cada módulo académico). Por eso se cerraron **antes** de escribir código: cambiarlas más tarde implica reescribir cimientos.

| ADR | Decisión | Estado |
|-----|----------|--------|
| **ADR-001** | **Auth propio** (email + password + 2FA TOTP, JWT access 15 min + refresh con rotación) para el MVP. **Moodle SSO** se incorpora para ALUMNOS en Fase 2 ([RF-47](./PRD.md#portal-del-alumno)). | ✅ **Cerrada** |
| **ADR-002** | **Multi-tenancy row-level**: una sola base de datos, columna `tenant_id` en toda tabla, repositories filtran por tenant por defecto. Database-per-tenant se reevaluará solo si un tenant exige aislamiento físico regulatorio. | ✅ **Cerrada** |
| **ADR-006** | **Modelo Materia + Dictado**: `Materia` es la definición única en el catálogo del tenant; `Dictado` es la instancia de esa materia en una `carrera × cohorte` concreta. Calificaciones, equipos docentes, encuentros y coloquios cuelgan del `Dictado`, no de `Materia`. Resuelve [OQ-01](./PRD.md#12-open-questions-a-resolver-antes-de-cerrar-el-prd). | ✅ **Cerrada** |

**Fundamento de cada cierre:**
- **ADR-001 (auth propio)**: no acopla el arranque a la configuración de Moodle de IT; ADMIN y FINANZAS pueden no ser usuarios de Moodle; el equipo controla el flujo completo. El SSO de alumnos llega cuando se construye el portal del alumno (Fase 2).
- **ADR-002 (row-level)**: con un solo tenant inicial, DB-per-tenant sería sobre-ingeniería (complejidad de migraciones, backups y pooling sin beneficio). Row-level cubre el aislamiento requerido y es el patrón estándar de SaaS a esta escala.
- **ADR-006 (Materia + Dictado)**: una misma materia se dicta en múltiples carreras/cohortes; separar catálogo de instancia evita duplicar definiciones y materializa el requisito de catálogo único con scoping.

### Decisiones pendientes — SE DEFINEN DURANTE EL DESARROLLO

> ⚠️ **Estas decisiones NO bloquean el arranque del desarrollo.** Cada una se resuelve cuando se llega a su módulo correspondiente (columna "Cuándo definir"). Son "habitaciones", no "cimientos": aislables, no transversales. El equipo de desarrollo las cierra sobre la marcha, documentando la decisión en este mismo archivo al momento de tomarla. Las que requieren definición de negocio (FINANZAS, semántica de NEXO) deben consultarse con el área correspondiente antes de implementar ese módulo, no antes de arrancar.

| ADR | Decisión | Cuándo definir (durante el desarrollo) |
|-----|----------|----------------------------------------|
| ADR-003 | Worker propio (asyncio/Celery/ARQ) vs N8N para la cola de comunicaciones | Al construir el módulo de comunicaciones |
| ADR-004 | Impersonation: token de sesión separado vs claim adicional en el JWT | Al implementar la feature de impersonation |
| ADR-005 | Estrategia de versionado de padrón (snapshot completo vs deltas) | Al construir el módulo de ingesta |
| ADR-007 | Fórmula de cálculo de Plus en liquidación (N comisiones, claves de Plus) | Antes de cerrar el módulo FINANZAS — **requiere definición del área de finanzas** |
| ADR-008 | Semántica y permisos del rol NEXO | Al poblar la matriz RBAC de NEXO (es data, no código) — **requiere definición de negocio** |

---

## 11. Capacidades propias del producto

Las siguientes capacidades son decisiones de diseño propias de activia-trace, reflejadas en el modelo y la arquitectura:

1. **Multi-tenancy nativo** — `Tenant` como raíz del modelo; aislamiento garantizado a nivel de repository (§6).
2. **Modelo de roles rico + RBAC fino** — roles ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS con permisos finos por feature (§5.2).
3. **Auth endurecida** — Argon2id, 2FA TOTP, access token 15 min + refresh rotation, impersonation permisada y auditada (§5.1, §5.3).
4. **Integración con Moodle Web Services** (`core_grades_get_grades`, etc.) + fallback de import manual (§7.1).
5. **Worker de cola de comunicaciones** con ciclo de vida, preview y aprobación humana opcional (§7.2).
6. **Audit log append-only sin límite** — toda acción queda atribuida al actor real (§5.4).
7. **Padrón versionado** y **catálogo único de materias** — sin upserts destructivos (§8).
8. **Identidad por UUID interno** — el legajo es atributo de negocio, nunca credencial ni selector de sesión (§8).
