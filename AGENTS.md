# activia-trace — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/`, `docs/ARQUITECTURA.md` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

**activia-trace** es una plataforma de gestión académica y trazabilidad multi-tenant que opera como capa de orquestación sobre Moodle: consolida calificaciones, detecta atrasos, gestiona comunicación saliente con aprobación, equipos docentes, encuentros, coloquios, liquidaciones de honorarios y auditoría completa. Cada institución es un tenant aislado; el nombre del producto es *trace* — todo audita.

---

## Stack Tecnológico

Detalle completo en [docs/ARQUITECTURA.md §2](docs/ARQUITECTURA.md). Resumen funcional en [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md).

### Backend
| Componente | Tecnología | Notas |
|------------|-----------|-------|
| Lenguaje | **Python 3.13** | snake_case en todo |
| Framework | **FastAPI** | API REST async |
| ORM | **SQLAlchemy 2.0** (async) | Queries SOLO en repositories |
| Migraciones | **Alembic** | Una migración por cambio de schema |
| Base de datos | **PostgreSQL** | JSONB para criterios/scores configurables |
| Validación | **Pydantic v2** | DTOs request/response; `extra='forbid'` |
| Auth | **JWT** (access corto + refresh rotation) + **Argon2id** | hashing de passwords |
| Cifrado en reposo | **AES-256** | PII sensible (CBU, DNI) y secretos |
| Background jobs | **Worker async** | cola de comunicaciones (Pend→Send→OK/Fail / Pend→Canc) |
| Integraciones | **N8N** + **Moodle Web Services** | cliente dedicado `moodle_ws.py` |
| Testing | **pytest** + coverage | ≥80% líneas, ≥90% reglas de negocio |

### Frontend
| Componente | Tecnología | Notas |
|------------|-----------|-------|
| Framework | **React 18** + **TypeScript** | Sin `any`, sin class components |
| Bundler | **Vite** | HMR en dev |
| Server state | **TanStack Query** | Todo fetch pasa por hooks de `services/` |
| Forms | **React Hook Form + Zod** | Validación tipada |
| Estilos | **Tailwind CSS** | Sin CSS modules, sin inline (salvo valores dinámicos) |
| HTTP | **Axios** | Cliente centralizado en `@/shared/services/api` |
| Estructura | **Feature-based modules** | `features/{name}/{components,hooks,services,types,pages}` |

### Infraestructura
| Componente | Tecnología |
|------------|-----------|
| Contenedores | **Docker** + docker-compose (local y prod) |
| Deploy | **Easypanel** |
| Observabilidad | Logs estructurados JSON + **OpenTelemetry** |

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/` (agnóstica de tecnología). El detalle técnico vive en `docs/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Sistema, integraciones, propiedades de seguridad |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos, matriz de capacidades, impersonación |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Funcionalidades por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E (importación, mensajería, auth) |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones y estructura de producto |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones cerradas y supuestos base |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |
| [11_historias_de_usuario.md](knowledge-base/11_historias_de_usuario.md) | Historias (Connextra) + criterios de aceptación |
| [docs/PRD.md](docs/PRD.md) | Requerimientos de producto y RNF |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Stack, Clean Architecture, estructura de directorios, seguridad |

> ⚠️ **Roles del dominio**: ALUMNO · TUTOR · PROFESOR · COORDINADOR · NEXO · ADMIN · FINANZAS. Leé `03_actores_y_roles.md` para internalizar el modelo de permisos ANTES de cualquier implementación.

> ⚠️ **Preguntas ALTA pendientes** (resolver antes de tocar el dominio afectado): **PA-01** catálogo de materias (Materia vs InstanciaDictado), **PA-07** cohortes ↔ carrera, **PA-22**/**PA-23** claves de Plus y acumulación en liquidaciones, **PA-25** semántica del rol NEXO. Ver [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md). No codees el módulo de liquidaciones (C-18) ni el de estructura académica (C-06) sin cerrar las preguntas que los bloquean.

---

## Skills Disponibles

Cargá la skill correspondiente al contexto **ANTES** de escribir código. Aplicá todos sus patrones.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / SQLAlchemy / migraciones / modelos | `fastapi-templates`, `postgresql-table-design`, `python-testing-patterns`, `test-driven-development` |
| **Backend Aux** | Servicios, integraciones, seguridad, performance | `api-security-best-practices`, `postgresql-optimization`, `systematic-debugging` |
| **Frontend** | React / TanStack / Tailwind / E2E | `typescript-advanced-types`, `tailwind-design-system`, `playwright-best-practices` |
| **DevOps** | Contenedores / build | `multi-stage-dockerfile` |
| **Transversal** | Calidad / revisión | `code-review-excellence`, `systematic-debugging` |
| **Orquestación** | SDD / OPSX / docs | `kb-creator`, `roadmap-generator`, `agent-instruction`, `find-skill` |

> **Gap conocido**: no hay skill de buenas prácticas React instalada (`vercel-react-best-practices` recomendada pero NO instalada por decisión del usuario). El stack queda cubierto ~100% por las skills preinstaladas.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 24 changes (`C-01`…`C-24`) en 6 fases, organizados con 11 gates de paralelismo y un plan óptimo de 3 agentes (Backend Core / Backend Aux / Frontend).
- **Camino crítico** (10 changes, mínimo irreducible): `C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-09 → C-10 → C-11 → C-12`. Es el flujo de mayor valor: importar → analizar → comunicar, en producción multi-tenant.
- **Primer change**: `C-01 foundation-setup` (infra, Docker, FastAPI skeleton, DB inicial, OpenTelemetry). Sin dependencias.
- **Primer fork** (GATE 4, tras `C-04 rbac`): seguridad lista → arrancan en paralelo `C-05 audit-log`, `C-06 estructura-academica` y `C-21 frontend-shell-y-auth`.

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá el change por su `C-NN`, respetá sus dependencias y leé los archivos de "Leer antes" de ese change.

---

## Reglas Duras (no negociables)

Estas reglas son **contrato**. Romperlas es un defecto, no una decisión de estilo. Ante conflicto entre la KB y este archivo, prevalecen las reglas duras.

### Generales
1. **No buildear automático.** Nunca ejecutar build/compile/bundle sin pedido explícito del usuario.
2. **No commitear sin pedido explícito.** `git add`/`commit`/`push` SOLO cuando el usuario lo pide. Si estás en la rama default, ramificá antes.
3. **Conventional Commits sin `Co-Authored-By`.** Formato `tipo(scope): mensaje`. Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`. Scopes: `auth`, `tenancy`, `users`, `alumnos`, `materias`, `comisiones`, `entregas`, `comunicacion`, `equipos`, `encuentros`, `coloquios`, `liquidaciones`, `auditoria`, `moodle`, `api`, `ui`. JAMÁS agregar atribución a IA ni `Co-Authored-By`.
4. **Tests sin mocks de DB.** Usar base real o contenedor de test (DB efímera). Mockear la base de datos invalida el test — no prueba nada.
5. **Pydantic schemas con `extra='forbid'`.** Todo schema rechaza campos no declarados (`model_config = ConfigDict(extra='forbid')`).
6. **snake_case en Python.** Funciones, variables, columnas de BD, módulos y paquetes.
7. **PascalCase en componentes React.** Nombre del componente y del archivo (`ProductCard.tsx`). Sin `any`, sin class components.

### Seguridad y arquitectura (fundacionales — fallan en code review)
8. **Identidad SIEMPRE desde la sesión** (JWT verificado). JAMÁS desde un parámetro de URL, body, header ni cualquier dato de la petición. Esto define quién es el usuario, sus roles y su tenant. Sin excepciones.
9. **Multi-tenancy row-level.** `tenant_id` en cada tabla; los repositories filtran por tenant **por defecto**. Un query sin scope de tenant es un bug que falla en code review.
10. **RBAC fino `modulo:accion`**, no flags binarios ni superusuario. Cada endpoint declara `require_permission(...)`. **Fail-closed**: sin permiso explícito → 403.
11. **Nunca lógica de negocio en Routers.** Nunca acceso directo a DB desde Services (siempre vía Repository). Flujo unidireccional Routers → Services → Repositories → Models.
12. **Secretos y PII (CBU, DNI) SIEMPRE AES-256.** Passwords con Argon2id. Nunca texto plano.
13. **Soft delete siempre** (auditoría append-only). Nunca hard delete.
14. **Identidad por UUID interno.** El legajo es un atributo de negocio, nunca credencial ni selector de sesión.
15. **≤500 LOC por archivo backend**, componentes React <200 LOC. Una migración Alembic por cambio de schema.
16. **Cobertura mínima**: ≥80% líneas, ≥90% reglas de negocio. **Strict TDD**: test que falla → código mínimo → triangulación → refactor.

---

## Agent Governance — Autonomía por dominio

La autonomía del agente depende de la criticidad del dominio que toca.

| Nivel | Dominios | Comportamiento |
|-------|----------|----------------|
| **CRÍTICO** | auth, multi-tenancy, RBAC, audit log, liquidaciones, core-models | Solo análisis y propuesta. NO escribir código sin aprobación humana explícita. |
| **MEDIO** | lógica de dominio, integraciones (Moodle/N8N), pipelines | Implementar con checkpoints; surfacear decisiones no obvias para revisión. |
| **BAJO** | CRUDs simples, pages frontend sin lógica crítica, catálogos, configuración | Autonomía total si pasan los tests. Reportar en el resumen. |

Antes de cualquier acción no trivial: identificá el nivel de governance del dominio. En CRÍTICO o sus equivalentes de seguridad, describí el cambio planeado y esperá confirmación antes de escribir.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/) + docs/ARQUITECTURA.md   → entender el dominio
2. Identificar el change en CHANGES.md (C-NN) + sus dependencias    → respetar gates
3. Verificar el nivel de governance del dominio                    → CRÍTICO = propuesta primero
4. /opsx:propose C-NN-nombre                                        → proposal + design + specs + tasks
5. Implementar las tasks (cargando skills, Strict TDD)             → respetando las reglas duras
6. /opsx:archive C-NN-nombre + marcar [x] en CHANGES.md            → cerrar el change
```

Aplicá TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
