## 1. Backend — Schemas (DTOs read-only)

- [ ] 1.1 Crear `app/schemas/alumno.py` con DTOs Pydantic v2 (`model_config = ConfigDict(extra='forbid')`): `CalificacionAlumnoRead` (actividad, nota_numerica, nota_textual, aprobado, estado_entrega), `MateriaCursadaRead` (materia_id, materia_nombre, avance_pct, total_actividades, aprobadas, calificaciones[]), `ColoquioReservadoRead` (evaluacion_id, materia_nombre, instancia, tipo, fecha, franja), `EstadoAcademicoRead` (avance_global_pct, total_actividades, aprobadas, materias[], coloquios_reservados[]).
- [ ] 1.2 RED+GREEN: test de schemas — `extra='forbid'` rechaza campos extra; los enums de `estado_entrega` (`aprobada`/`con_nota`/`sin_entrega`) validan; `from_attributes` mapea desde objetos ORM/dict. Triangular con al menos un caso válido y uno inválido por schema clave.

## 2. Backend — Repository (queries read-only, scoped por tenant + alumno)

- [ ] 2.1 Crear `app/repositories/alumno_repository.py` con `AlumnoRepository(TenantScopedRepository)`. Método `get_entradas_padron_activas(usuario_id)` → entradas del alumno (no soft-deleted) en versiones activas, con join a `Materia` para nombre. Filtra SIEMPRE por `tenant_id` + `usuario_id`.
- [ ] 2.2 Método `get_calificaciones_por_entradas(entrada_padron_ids)` → calificaciones del alumno agrupables por materia (no soft-deleted), filtrado por tenant.
- [ ] 2.3 Método `get_reservas_activas(usuario_id)` → reservas `Activa` del alumno con join a `Evaluacion`/`TurnoEvaluacion`/`Materia` para materia, instancia, tipo, fecha, franja. Filtra por tenant + `alumno_id`.
- [ ] 2.4 RED: tests de repository contra DB real/efímera (sin mocks de DB). Casos: alumno con entradas/calificaciones/reservas; alumno sin `usuario_id` reconciliado (no aparece); aislamiento por tenant (datos de otro tenant nunca se devuelven); reservas canceladas excluidas. Triangular cada método con ≥2 casos.

## 3. Backend — Service (lógica de presentación: avance + clasificación)

- [ ] 3.1 Crear `app/services/alumno_service.py` con `AlumnoService`. Método `get_estado_academico(current_user)` que orquesta el repository y arma `EstadoAcademicoRead`.
- [ ] 3.2 Función pura `clasificar_estado_entrega(calificacion)` → `aprobada` / `con_nota` / `sin_entrega` según `aprobado` y presencia de nota (D4). RED+GREEN+triangulación con los 3 casos.
- [ ] 3.3 Función pura `calcular_avance(aprobadas, total)` → pct redondeado, 0 si total=0 (sin división por cero). RED+GREEN+triangulación: 3/4→75, 0/0→0, 4/4→100.
- [ ] 3.4 Avance global ponderado por cantidad de actividades sobre todas las materias. Test con varias materias.
- [ ] 3.5 RED: test de servicio (identidad SIEMPRE desde `current_user`; el servicio nunca recibe `alumno_id` por otra vía).

## 4. Backend — Router + registro

- [ ] 4.1 Crear `app/api/v1/routers/alumno.py` con `GET /alumno/estado-academico`, `response_model=EstadoAcademicoRead`, `Depends(require_permission("academico:ver_propio"))` y `current_user = Depends(get_current_user)`. Sin parámetros de identidad en la firma. Construir repo+service con `current_user.tenant_id`.
- [ ] 4.2 Registrar el router en `app/api/v1/routers/__init__.py` (incluir en el agregador con el resto de routers v1).
- [ ] 4.3 RED: tests de router (integración). Casos: ALUMNO con permiso → 200 y payload correcto; usuario sin permiso → 403 (fail-closed); sin token → 401; aislamiento por tenant/alumno. Sin mocks de DB.

## 5. Frontend — Feature `mi-cursada` (tipos, servicio, hook)

- [ ] 5.1 Crear `features/mi-cursada/types/index.ts` con los tipos TS que reflejan `EstadoAcademicoRead` (sin `any`).
- [ ] 5.2 Crear `features/mi-cursada/services/miCursadaService.ts` con `getEstadoAcademico()` usando el cliente Axios centralizado (`@/shared/services/api`) → `GET /api/v1/alumno/estado-academico`.
- [ ] 5.3 Crear `features/mi-cursada/hooks/miCursadaHooks.ts` con `useEstadoAcademico()` (TanStack Query). Test del hook (loading/success/error).

## 6. Frontend — Página y componentes

- [ ] 6.1 Crear `features/mi-cursada/components/AvanceKpis.tsx` (<200 LOC) con `KpiCard` para avance global, materias y aprobadas.
- [ ] 6.2 Crear `features/mi-cursada/components/MateriasCursadasTable.tsx` (<200 LOC) usando `TableWrapper`/`Card` + `StatusBadge` para el estado de cada actividad.
- [ ] 6.3 Crear `features/mi-cursada/components/ColoquiosReservadosPanel.tsx` (<200 LOC) con la lista de reservas activas y `EmptyState` cuando no hay.
- [ ] 6.4 Crear `features/mi-cursada/pages/MiCursadaPage.tsx` (<200 LOC): `PageHeader` "Mi cursada", gating por rol ALUMNO con `useAuth` (acceso denegado si no es ALUMNO), estados loading/error, `EmptyState` para sin materias. Wrapper raíz SIN `max-w-*` ni `mx-auto` (el `AppLayout` provee el padding).
- [ ] 6.5 RED+GREEN: test de `MiCursadaPage` — render para ALUMNO con datos; acceso denegado para rol no ALUMNO; estados vacíos.

## 7. Frontend — Integración nav + ruta

- [ ] 7.1 Agregar a `features/shell/components/buildNav.ts` el ítem `{ label: 'Mi cursada', path: '/mi-cursada', roles: ['ALUMNO'], icon: 'book', group: 'MI CURSADA' }`.
- [ ] 7.2 Test de `buildNav`: ALUMNO ve el ítem `MI CURSADA`; otros roles no lo ven.
- [ ] 7.3 Registrar en `App.tsx` la ruta `/mi-cursada` con `ProtectedRoute requiredRoles={['ALUMNO']}` y la página lazy-loaded.

## 8. Verificación final

- [ ] 8.1 Correr toda la suite backend (pytest) y frontend (vitest) — todo verde, sin romper tests preexistentes.
- [ ] 8.2 Verificar cobertura: ≥80% líneas, ≥90% en la lógica de avance/clasificación (reglas de negocio).
- [ ] 8.3 Confirmar reglas duras: identidad desde JWT, scope por tenant en cada query, `require_permission` fail-closed, flujo Router→Service→Repository→Model, `extra='forbid'`, ≤500 LOC backend / <200 LOC componentes, sin `max-w-*`/`mx-auto` en wrapper raíz.
