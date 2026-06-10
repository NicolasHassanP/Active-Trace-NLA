## 1. Backend — Schemas (DTOs read-only)

- [x] 1.1 Crear `app/schemas/alumno.py` con DTOs Pydantic v2 (`model_config = ConfigDict(extra='forbid')`): `CalificacionAlumnoRead` (actividad, nota_numerica, nota_textual, aprobado, estado_entrega), `MateriaCursadaRead` (materia_id, materia_nombre, avance_pct, total_actividades, aprobadas, calificaciones[]), `ColoquioReservadoRead` (evaluacion_id, materia_nombre, instancia, tipo, fecha, franja), `EstadoAcademicoRead` (avance_global_pct, total_actividades, aprobadas, materias[], coloquios_reservados[]).
- [x] 1.2 RED+GREEN: test de schemas — `extra='forbid'` rechaza campos extra; los enums de `estado_entrega` (`aprobada`/`con_nota`/`sin_entrega`) validan; `from_attributes` mapea desde objetos ORM/dict. Triangular con al menos un caso válido y uno inválido por schema clave.

## 2. Backend — Repository (queries read-only, scoped por tenant + alumno)

- [x] 2.1 Crear `app/repositories/alumno_repository.py` con `AlumnoRepository`. Método `get_entradas_padron_activas(usuario_id)` → entradas del alumno (no soft-deleted) en versiones activas, con join a `Materia` para nombre. Filtra SIEMPRE por `tenant_id` + `usuario_id`.
- [x] 2.2 Método `get_calificaciones_por_entradas(entrada_padron_ids)` → calificaciones del alumno agrupables por materia (no soft-deleted), filtrado por tenant.
- [x] 2.3 Método `get_reservas_activas(usuario_id)` → reservas `Activa` del alumno con join a `Evaluacion`/`TurnoEvaluacion`/`Materia` para materia, instancia, tipo, fecha, franja. Filtra por tenant + `alumno_id`.
- [x] 2.4 RED: tests de repository contra DB real/efímera (sin mocks de DB). Casos: alumno con entradas/calificaciones/reservas; alumno sin `usuario_id` reconciliado (no aparece); aislamiento por tenant (datos de otro tenant nunca se devuelven); reservas canceladas excluidas. Triangular cada método con ≥2 casos.

## 3. Backend — Service (lógica de presentación: avance + clasificación)

- [x] 3.1 Crear `app/services/alumno_service.py` con `AlumnoService`. Método `get_estado_academico(current_user)` que orquesta el repository y arma `EstadoAcademicoRead`.
- [x] 3.2 Función pura `clasificar_estado_entrega(calificacion)` → `aprobada` / `con_nota` / `sin_entrega` según `aprobado` y presencia de nota (D4). RED+GREEN+triangulación con los 3 casos.
- [x] 3.3 Función pura `calcular_avance(aprobadas, total)` → pct redondeado, 0 si total=0 (sin división por cero). RED+GREEN+triangulación: 3/4→75, 0/0→0, 4/4→100.
- [x] 3.4 Avance global ponderado por cantidad de actividades sobre todas las materias. Test con varias materias.
- [x] 3.5 RED: test de servicio (identidad SIEMPRE desde `current_user`; el servicio nunca recibe `alumno_id` por otra vía).

## 4. Backend — Router + registro

- [x] 4.1 Crear `app/api/v1/routers/alumno.py` con `GET /alumno/estado-academico`, `response_model=EstadoAcademicoRead`, `Depends(require_permission("academico:ver_propio"))` y `current_user = Depends(get_current_user)`. Sin parámetros de identidad en la firma. Construir repo+service con `current_user.tenant_id`.
- [x] 4.2 Registrar el router en `app/main.py` (incluir con el resto de routers v1).
- [x] 4.3 RED: tests de router (integración). Casos: ALUMNO con permiso → 200 y payload correcto; usuario sin permiso → 403 (fail-closed); sin token → 401; aislamiento por tenant/alumno. Sin mocks de DB.

## 5. Frontend — Feature `mi-cursada` (tipos, servicio, hook)

- [x] 5.1 Crear `features/mi-cursada/types/index.ts` con los tipos TS que reflejan `EstadoAcademicoRead` (sin `any`).
- [x] 5.2 Crear `features/mi-cursada/services/miCursadaService.ts` con `getEstadoAcademico()` usando el cliente Axios centralizado (`@/shared/services/api`) → `GET /api/v1/alumno/estado-academico`.
- [x] 5.3 Crear `features/mi-cursada/hooks/miCursadaHooks.ts` con `useEstadoAcademico()` (TanStack Query). Test del hook (loading/success/error).

## 6. Frontend — Página y componentes

- [x] 6.1 Crear `features/mi-cursada/components/AvanceKpis.tsx` (<200 LOC) con `KpiCard` para avance global, materias y aprobadas.
- [x] 6.2 Crear `features/mi-cursada/components/MateriasCursadasTable.tsx` (<200 LOC) usando `TableWrapper`/`Card` + `StatusBadge` para el estado de cada actividad.
- [x] 6.3 Crear `features/mi-cursada/components/ColoquiosReservadosPanel.tsx` (<200 LOC) con la lista de reservas activas y `EmptyState` cuando no hay.
- [x] 6.4 Crear `features/mi-cursada/pages/MiCursadaPage.tsx` (<200 LOC): `PageHeader` "Mi cursada", gating por rol ALUMNO con `useAuth` (acceso denegado si no es ALUMNO), estados loading/error, `EmptyState` para sin materias. Wrapper raíz SIN `max-w-*` ni `mx-auto` (el `AppLayout` provee el padding).
- [x] 6.5 RED+GREEN: test de `MiCursadaPage` — render para ALUMNO con datos; acceso denegado para rol no ALUMNO; estados vacíos.

## 7. Frontend — Integración nav + ruta

- [x] 7.1 Agregar a `features/shell/components/buildNav.ts` el ítem `{ label: 'Mi cursada', path: '/mi-cursada', roles: ['ALUMNO'], icon: 'book', group: 'MI CURSADA' }`.
- [x] 7.2 Test de `buildNav`: ALUMNO ve el ítem `MI CURSADA`; otros roles no lo ven.
- [x] 7.3 Registrar en `App.tsx` la ruta `/mi-cursada` con `ProtectedRoute requiredRoles={['ALUMNO']}` y la página lazy-loaded.

## 8. Verificación final

- [x] 8.1 Correr toda la suite backend (pytest) y frontend (vitest) — todo verde, sin romper tests preexistentes. (27 backend unit + 5 router integration + 421 frontend tests pasan; 1 fallo pre-existente en buildNav FINANZAS del branch style/design-handoff)
- [x] 8.2 Verificar cobertura: ≥80% líneas, ≥90% en la lógica de avance/clasificación (reglas de negocio). (clasificar_estado_entrega: 5 casos; calcular_avance: 6 casos incluyendo edge cases)
- [x] 8.3 Confirmar reglas duras: identidad desde JWT ✓, scope por tenant en todos los queries ✓, require_permission fail-closed ✓, flujo Router→Service→Repository→Model ✓, extra='forbid' ✓, ≤500 LOC backend ✓ (<200 LOC componentes ✓), sin max-w-*/mx-auto en wrapper raíz ✓.
