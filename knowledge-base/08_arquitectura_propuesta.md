# 08 — Arquitectura (resumen)

> **Propósito**: describir la arquitectura OBJETIVO de activia-trace — el sistema a construir — en lenguaje de dominio y técnico-destino. Este archivo es un resumen ejecutivo orientado a cualquier equipo que tome el producto: muestra el patrón, el modelo de seguridad, las integraciones y las decisiones clave. El detalle completo y las convenciones de código viven en [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

---

## 1. Filosofía y principios rectores

activia-trace adopta **Clean Architecture por capas** con separación estricta de responsabilidades. Los principios que guían cada decisión son:

1. **Conceptos antes que código** — la arquitectura se diseña y documenta antes de escribir una línea. Este archivo y [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md) son el contrato.
2. **Separación estricta de capas** — la lógica de negocio no toca la capa de transporte HTTP ni la de persistencia directamente.
3. **La identidad jamás se deriva de un parámetro de la petición** — regla de seguridad #1, no negociable.
4. **Multi-tenant desde el día 0** — no es un retrofit; es la raíz de todo el modelo de datos y de permisos.
5. **Todo audita** — el nombre del producto es *trace*. Cada acción significativa queda registrada y atribuida.

---

## 2. Patrón arquitectónico

### Backend — API REST por capas (Clean Architecture)

El flujo de una petición es **unidireccional**, sin saltos entre capas:

```
PETICIÓN HTTP
     │
     ▼
┌─────────────┐  Validación de entrada, autenticación y autorización.
│   Routers   │  NADA de lógica de negocio.
└──────┬──────┘
       ▼
┌─────────────┐  Reglas de negocio, orquestación de casos de uso.
│  Services   │  NO accede a la base de datos directamente.
└──────┬──────┘
       ▼
┌─────────────┐  Todas las consultas a la base de datos.
│Repositories │  NADA de reglas de negocio. Scope de tenant siempre activo.
└──────┬──────┘
       ▼
┌─────────────┐  Entidades del dominio (ORM).
│   Models    │
└──────┬──────┘
       ▼
  Base de datos relacional (PostgreSQL)
```

**Reglas no negociables de la capa:**
- Los Routers no ejecutan lógica de negocio.
- Los Services no emiten SQL directamente.
- Todo Repository filtra por `tenant_id` por defecto. Un query sin scope de tenant es un bug que debe fallar en code review.
- Soft delete siempre; nunca borrado físico (preserva auditoría).
- Secretos externos cifrados en reposo; nunca en texto plano.

### Frontend — SPA organizada por features

El frontend es una **Single Page Application** estructurada por módulos de negocio (features). Cada feature agrupa sus propios componentes, hooks, servicios, tipos y páginas. Toda comunicación con el backend pasa por un cliente HTTP centralizado que maneja autenticación y refresh de tokens de forma transparente.

### Infraestructura

El sistema se despliega en **contenedores** (Docker + Docker Compose para desarrollo local y producción). El entorno de producción usa orquestación vía panel de control (Easypanel). Observabilidad con logs estructurados en JSON y trazas distribuidas (OpenTelemetry).

---

## 3. Modelo de seguridad

La seguridad es el corazón del diseño. Ver la especificación completa en [`../docs/ARQUITECTURA.md §5`](../docs/ARQUITECTURA.md).

### 3.1 Autenticación

- Inicio de sesión con **email + contraseña**. Contraseña almacenada con hashing seguro (Argon2id); nunca en texto plano.
- **Autenticación de dos factores (2FA)** opcional por usuario (TOTP).
- Recuperación de contraseña por email con **token de un solo uso** y expiración corta.
- La sesión se representa como un **JWT firmado** de vida corta (access token, 15 minutos) más un **refresh token con rotación** (un refresh usado se invalida inmediatamente).
- El JWT lleva solo los claims mínimos: identificador de usuario, `tenant_id`, roles y expiración. Los permisos se resuelven server-side en cada petición, nunca se almacenan en el token.

### 3.2 Autorización — RBAC con permisos finos

- Roles del dominio: **ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS** (ver [03 — Actores y Roles](03_actores_y_roles.md)).
- **No existe un flag binario de superusuario.** Cada acción protegida requiere un permiso explícito del tipo `modulo:accion`.
- Cada endpoint declara el permiso que exige. Si el usuario no lo tiene → acceso denegado.
- La matriz rol × permiso es un **catálogo administrable**, no código hardcodeado.

### 3.3 Regla de oro de identidad

> **La identidad, los roles y el tenant del usuario se derivan EXCLUSIVAMENTE del JWT verificado.** Ningún dato de la petición (query string, body, header) puede alterar quién es el usuario ni qué permisos tiene. Cualquier `id` o identificador que llegue en la petición se trata como dato de negocio a validar contra los permisos del usuario autenticado, nunca como su identidad.

El identificador interno del usuario es un **UUID** generado por el sistema. El legajo académico, si se registra, es solo un **atributo de negocio** — nunca credencial, nunca selector de identidad, nunca aparece en URLs como sustituto de la sesión.

### 3.4 Defensas transversales

| Defensa | Descripción |
|---------|-------------|
| TLS 1.3 | Todo el tráfico cifrado en tránsito. |
| Cifrado en reposo | Datos personales sensibles (CBU, DNI) cifrados con AES-256. |
| CSRF | Protección en todos los endpoints que modifican estado. |
| Rate limiting | Por IP y por usuario, para mitigar fuerza bruta y abuso. |
| Audit log append-only | Sin límite de retención; sin posibilidad de edición ni borrado. |

### 3.5 Impersonación (suplantación legítima)

Un usuario autorizado (soporte, ADMIN) puede operar temporalmente en nombre de otro usuario para diagnóstico. Es una **feature explícita y controlada**:

- Requiere el permiso `impersonacion:usar`.
- Genera una sesión distinguible de una sesión normal.
- Toda acción bajo impersonación queda atribuida al **actor real** (quien impersona), no a la persona impersonada.
- Cada inicio y fin de impersonación se registra en el audit log: quién, a quién, desde cuándo, hasta cuándo.

---

## 4. Multi-tenancy

El sistema es **multi-institución (multi-tenant)**. Una institución = un tenant. Los datos de distintos tenants **nunca se cruzan**.

- El `tenant_id` se resuelve del JWT autenticado y se inyecta como dependencia en cada request.
- Los repositories aplican el scope de tenant en todas las queries por defecto.
- Configuración por tenant: plantillas de comunicación, escalas de calificación, flag de aprobación de comunicaciones masivas, branding.
- La estrategia de aislamiento físico (row-level security vs. base de datos por tenant) se define en ADR-002 (ver [`../docs/ARQUITECTURA.md §10`](../docs/ARQUITECTURA.md)).

---

## 5. Integraciones

### 5.1 LMS (Moodle) — Web Services

- Sincronización de calificaciones, usuarios y actividades vía **Moodle Web Services** (API estándar del LMS).
- **Sync nocturna automática** más sync on-demand cuando el usuario lo solicita.
- **Fallback de importación manual**: para tenants cuyo Moodle no exponga Web Services, se acepta carga de archivos `.xlsx`/`.csv` con la convención de columnas definida en [06 — Funcionalidades](06_funcionalidades.md). Preserva el flujo de trabajo conocido.
- Los errores de integración mapean a respuesta `502` con mecanismo de reintento.

### 5.2 Worker de cola de comunicaciones

- Cola de mensajes asíncrona con ciclo de vida: **Pendiente → Enviando → OK / Fallido** y ruta de cancelación (**Pendiente → Cancelado**).
- **Preview obligatorio** antes de encolar cualquier comunicación masiva.
- **Aprobación humana configurable por tenant**: si está activa, un usuario con permiso `comunicacion:aprobar` debe aprobar el lote antes de que el worker lo procese.
- Plantillas con variables de sustitución (nombre del alumno, materia, etc.).

### 5.3 Exportación de datos

- El sistema puede generar archivos descargables (`.xlsx`, `.csv`) para reportes y para la carga inversa en el LMS.
- El formato de exportación respeta las convenciones del LMS destino para facilitar la importación sin retrabajos.

---

## 6. Persistencia

- Base de datos **relacional** (PostgreSQL) como sistema de registro.
- **JSONB** para estructuras configurables por tenant (criterios de evaluación, escalas textuales, scores).
- **Migraciones versionadas** (Alembic): una migración por cambio de schema, nunca cambios manuales en producción.
- **Soft delete**: las entidades no se borran físicamente; se marcan como inactivas/eliminadas con timestamp. El histórico se conserva para auditoría y para clonado entre períodos académicos.
- Modelo de datos detallado en [04 — Modelo de Datos](04_modelo_de_datos.md).

---

## 7. Observabilidad y operación

- **Logs estructurados en JSON** en todos los servicios (backend, worker, integraciones).
- **Trazas distribuidas** (OpenTelemetry) para correlacionar peticiones a través de servicios.
- **Audit log de negocio** separado del log técnico: registra acciones significativas de usuarios (quién, qué, sobre qué entidad, desde qué tenant, con qué resultado). Append-only, sin límite de retención.
- CI/CD automatizado: build + tests + lint + deploy en cada merge a la rama principal.

---

## 8. Decisiones de arquitectura pendientes

Las decisiones abiertas se gestionan como ADRs (Architecture Decision Records). Las principales:

| ADR | Decisión pendiente |
|-----|--------------------|
| ADR-001 | ¿Auth propio (email + contraseña) vs. federado con Moodle SSO? |
| ADR-002 | Multi-tenancy: row-level security (columna `tenant_id`) vs. base de datos por tenant. |
| ADR-003 | Worker de mails: implementación propia (asyncio / Celery / ARQ) vs. orquestador externo (N8N). |

El detalle de cada ADR y su resolución viven en [`../docs/ARQUITECTURA.md §10`](../docs/ARQUITECTURA.md).

---

## 9. Para el equipo de implementación

1. **Clean Architecture estricta**: Routers → Services → Repositories → Models → DB. Sin saltear capas.
2. **Multi-tenant desde el día 0**: toda tabla de datos del dominio lleva `tenant_id`. Todo query lleva scope de tenant.
3. **Identidad exclusivamente desde el JWT verificado**: ningún parámetro de request puede cambiar quién es el usuario.
4. **RBAC con permisos finos**: sin flags binarios; la matriz rol × permiso es un catálogo en base de datos.
5. **Audit log append-only, sin límite**: toda acción significativa queda registrada con actor, tenant, timestamp y resultado.
6. **Soft delete siempre**: el historial se preserva para auditoría y para clonado entre períodos.
7. **Integraciones aisladas**: el cliente del LMS y el worker de mails son módulos independientes; sus errores no rompen el flujo principal.

> El detalle completo — stack tecnológico, estructura de directorios, convenciones de código, variables de entorno y ADRs — vive en [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).
