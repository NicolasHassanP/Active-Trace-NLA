# HANDOFF — Re-aplicar fixes perdidos + bugs reales (2026-06-09)

> Para el compañero que continúa desde su PC. Generado al cierre de una sesión en `style/design-handoff`.
> Todo lo de acá ya fue **implementado y verificado verde una vez**, pero se perdió del working tree (ver "Contexto crítico"). Re-aplicarlo es mecánico: el detalle por-archivo está abajo.
> Detalle adicional en Engram (topic_keys citados). Hacé `git pull` + `engram sync --import` antes de arrancar.

---

## ⚠️ Contexto crítico — por qué se perdió trabajo

El repo de esta máquina vive en **OneDrive** (`C:\Users\Nico\OneDrive\...`). Durante una sesión con varios sub-agentes escribiendo archivos en ráfaga, **OneDrive restauró versiones viejas de la nube** y revirtió la mayoría de los cambios: solo sobrevivieron los archivos escritos por la última tanda. Engram: `infra/onedrive-revierte-cambios`.

**Antes de empezar a editar:**
- Trabajá desde un path **NO sincronizado por OneDrive** (ej. cloná/mové el repo a `C:\dev\active-trace`). Si tu clon ya está fuera de OneDrive, no hay problema.
- Si estás obligado a usar OneDrive, **pausá la sincronización** antes de editar (bandeja → ícono nube → Pausar 8h; o matar el proceso `OneDrive.Sync.Service.exe`).

## ⚠️ Reglas al re-aplicar (no negociables)

1. **NO corras la suite completa de pytest** — es lenta y deja shells colgados. Verificá **por-archivo**: desde `backend/` → `python -m pytest tests/<archivo> -q --tb=short`. Engram: `workflow/no-full-pytest-suite`.
2. **USÁ los helpers que ya están en `conftest.py`** (ver "Ya hecho"), no los recrees.
3. `domain_user_id` se pasa como **keyword**; verificá la firma real del método en `backend/app/services/` antes de editar.
4. No commitees hasta verificar el archivo.

---

## ✅ Ya hecho (commiteado en esta rama)

- **`backend/tests/conftest.py`** — dos helpers nuevos:
  - `delete_audit_events_for_tenant(session, tenant_id)` (~línea 535): borra `audit_event` respetando el trigger de inmutabilidad (DISABLE/ENABLE TRIGGER). Usar en teardowns en vez de `DELETE FROM audit_event`. Engram: `tests/audit-event-teardown-strategy`.
  - `create_usuario_con_identidad(session, tenant_id, *, email=None, nombre="Test", apellidos="User", roles=None, **extra) -> Usuario` (~línea 600): crea una fila `AuthIdentity` real + `Usuario` linkeado, garantizando el invariante C-28 `auth_identity_id ≠ usuario.id`. Para endpoint tests: usar `usuario.auth_identity_id` como `sub` del JWT y `usuario.id` como `domain_user_id`. Engram: `tests/usuario-con-identidad-helper`.
- **`test_encuentros.py`, `test_inbox_router.py`, `test_perfil_router.py`** — migrados al helper `create_usuario_con_identidad` (10/10, 12/12, 14/15 respectivamente).

---

## 📋 TAREA A — Frontend sección 1 (bugs reales, ALTA)

Causa raíz: enums del frontend desalineados con el backend (case/acentos). Engram: `frontend/enum-mismatch-dias-estados`.
Verificación final: desde `frontend/` → `npx tsc --noEmit` (0 errores) + `npx vitest run src/features/encuentros-coord src/features/coloquios`.

1. **`frontend/src/features/encuentros-coord/types/index.ts`**
   - `DiaSemana` → `'Lunes' | 'Martes' | 'Miércoles' | 'Jueves' | 'Viernes' | 'Sábado' | 'Domingo'` (capitalizado + acentos; valores exactos del enum en `backend/app/models/encuentro.py`).
   - `InstanciaEncuentroEstado` → `'Programado' | 'Realizado' | 'Cancelado'` (quitar `'postergado'`, no existe en backend).
   - Agregar constante `DIAS_SEMANA` (espejá el patrón de `frontend/src/features/guardias/types/index.ts`).
2. **`frontend/src/features/encuentros-coord/components/GuardiasFilters.tsx`** — actualizar el array `DIAS` a los valores correctos.
3. **`frontend/src/features/encuentros-coord/components/CrearSlotDialog.tsx`** — array `DIAS` correcto; default `dia_semana: 'Lunes'`; simplificar el render del label de la option (ya no hace falta el hack `charAt(0).toUpperCase()`).
4. **Tests de `encuentros-coord`** (`hooks/__tests__`, `pages/__tests__`, `services/__tests__`) — actualizar fixtures: `dia: 'lunes'→'Lunes'`, `estado: 'programado'→'Programado'`, y params de filtro en los queryKey/transport tests.
5. **`frontend/src/features/coloquios/types/index.ts`** — `EvaluacionTipo` → `'Parcial' | 'TP' | 'Coloquio' | 'Recuperatorio'`; `ReservaEstado` → `'Activa' | 'Cancelada'` (coincidir con backend). Actualizar fixtures en los 4 test files de coloquios (`coloquiosHooks`, `coloquiosService`, `convocatoriaSchema`, `ColoquiosPage`).
6. **`frontend/src/features/tareas/components/TareasAdminTable.tsx`** — la prop `onDelegar` estaba declarada pero sin usar (TS6133). Agregar un botón "Delegar" junto a "Avanzar" usando `onDelegar(tarea.id)` (consistente con `handleDelegar` en `TareasPage.tsx`).

---

## 📋 TAREA B — Backend tests C-28 + teardown audit_event

C-28: varios services exigen `domain_user_id` (usuario.id de dominio ≠ auth_identity_id del JWT). Producción está OK; faltan los tests. Engram: `tests/c28-domain-user-id-callsites`, `tests/c28-residual-buckets`.

1. **`test_calificaciones.py`** (7 call-sites) — `importar()`/`importar_with_report()` → `domain_user_id=profesor.id` (profesor real de `_create_cal_context()`; en scope-isolated usar `profesor_a.id`/`profesor_b.id`). Reemplazar `DELETE FROM audit_event` en `_cleanup_cal()` por `delete_audit_events_for_tenant`.
2. **`test_calificaciones_router.py`** — reemplazar `DELETE FROM audit_event` en `_cleanup_router()` por el helper. (Router-only vía TestClient: no requiere domain_user_id.)
3. **`test_padron.py`** (9 call-sites) — `activar()`/`vaciar()`/`sync_from_moodle()` → `domain_user_id=usuario.id` (id correcto del actor). Assert `version.cargado_por == current_user.user_id` → `== usuario.id`. Los 2 endpoint tests que daban 500 (`test_activar_endpoint_creates_version`, `test_vaciar_endpoint_403_on_other_user_version`): reescribir `_create_test_usuario()` con `create_usuario_con_identidad`, usar `usuario.auth_identity_id` como JWT sub, y limpiar `auth_identities` en `_cleanup_padron`. Reemplazar `DELETE FROM audit_event` por el helper.
4. **`test_comunicacion_service.py`** — reemplazar ~6 `DELETE FROM audit_event` inline (bloques `finally`) por `delete_audit_events_for_tenant`. Verificar que encolar/aprobar_lote/aprobar_individual pasen `domain_user_id`.
5. **`test_c27_historial_comunicaciones.py`** — reemplazar `DELETE FROM audit_event` (en `_cleanup()` y teardown del fixture `c27_data`) por el helper.
6. **`test_evaluacion_service.py`** (13 call-sites) — `crear_reserva()`/`cancelar_reserva()`/`get_resultado_alumno()`/`listar_mis_convocatorias()` → `domain_user_id=al.id` (alumnos reales de `_create_usuario()`). **Guard `audit_action`**: el fixture module-scoped hace `ALTER TYPE audit_action ADD VALUE` sobre una DB sin el enum base → `UndefinedObjectError`. Agregar ANTES del ALTER: `DO $$ BEGIN CREATE TYPE audit_action AS ENUM (<valores base>) EXCEPTION WHEN duplicate_object THEN NULL; END $$;` (copiar valores exactos de cómo lo crea `conftest._ensure_schema` / la migración en `backend/alembic/`).
7. **`test_guardias.py`** (8 call-sites) — `registrar()`/`consultar()`/`editar()`/`exportar()` → `domain_user_id=` (tutor: id de dominio del tutor; coordinador rol global: el branch se ignora). Los 2 endpoint tests 500 (`test_registrar_guardia_endpoint_creates_guardia`, `test_export_guardias_endpoint_returns_csv`): `grd_setup` debe crear AuthIdentity reales (`create_usuario_con_identidad`) y los `_make_jwt` usar `usuario.auth_identity_id`. **CSV stale**: `test_exportar_guardias_genera_csv` asertaba `"asignacion_id" in header` — el header real es `guardia_id,materia,carrera,cohorte,docente,dia,horario,estado,comentarios,creada_at` (sin `asignacion_id`, diseño superado). Quitar ese assert (dejar comentario). Confirmar header leyendo `backend/app/services/guardia_service.py`.
8. **`services/test_tarea_service.py`** (14 call-sites) — `publicar()`/`cambiar_estado()`/`delegar()`/`comentar()`/`listar_mias()` → `domain_user_id=` (coord/docente/tercero/foraneo según actor). OJO: `listar_mias()` cambió a tomar **solo** `domain_user_id` (sin `current_user`) — verificar firma. Mismo guard `CREATE TYPE audit_action ... EXCEPTION` que en (6).

---

## 📋 TAREA C — Seed 4.3 (BAJO)

**`backend/seed_rbac_demo.py`** — junto a la entrada `('guardias:registrar', ...)` en el catálogo `PERMISOS`, agregar comentario (NO eliminar el permiso, NO tocar grants):
```python
# RESERVADO — guardias:registrar existe en el catálogo pero ningún router lo consume.
# Las guardias se gestionan con encuentros:gestionar (decisión C-13). Reservado para uso futuro.
```

---

## 🐛 Hallazgos de PRODUCCIÓN (decidir aparte — NO son test-infra)

Quedaron expuestos al limpiar la infra de tests. Governance MEDIO (dominio), requieren decisión antes de tocar producción:

1. **`EncuentroService.listar_instancias` no filtra por asignaciones del PROFESOR** — un PROFESOR ve encuentros que no son suyos. Lo destapa `test_encuentros::test_listar_encuentros_profesor_ve_solo_propios` (1 test rojo legítimo). Es un bug real de scope/RN.
2. **`test_guardias` posibles residuales** (`TypeError: GuardiaRead`, HTTP 500) a verificar tras re-aplicar la Tarea B — clasificar si son schema/producción o test-stale.

---

## Estado esperado tras completar A+B+C

~110 tests que estaban en rojo vuelven a verde (51 call-sites C-28 + ~60 de audit_action/router/CSV/AuthIdentity, ya verificados una vez). Queda el bug real de encuentros (#1) como trabajo de producción separado.
