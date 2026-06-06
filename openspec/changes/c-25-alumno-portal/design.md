## Context

El rol ALUMNO existe en el modelo de seguridad y posee el permiso `academico:ver_propio` (asignado `global` en `seed_rbac_demo.py`), pero no hay ningún endpoint ni pantalla que lo consuma. El alumno es un caso particular del dominio: **no se modela como `Asignacion`** (el enum `RolAsignacion` excluye explícitamente ALUMNO — ver `app/models/usuario.py`), sino que su condición de alumno vive en el **padrón** (`EntradaPadron`). El vínculo entre la cuenta del alumno y sus datos académicos es `EntradaPadron.usuario_id` (nullable, FK→`usuario`, ON DELETE SET NULL).

Estado actual relevante de los datos:
- `Calificacion` cuelga de `EntradaPadron` (`entrada_padron_id`) y tiene `materia_id` desnormalizado y `aprobado` persistido.
- `EntradaPadron` pertenece a una `VersionPadron` (materia × cohorte), con cursor `activa`.
- `ReservaEvaluacion` vincula directo `alumno_id` → `usuario.id`, con `estado` Activa/Cancelada y `evaluacion_id`/`turno_id`.
- `Evaluacion` (tipo Coloquio entre otros) + `TurnoEvaluacion` (fecha, franja) dan el contexto del coloquio reservado.

Restricciones de proyecto (reglas duras): identidad desde JWT, multi-tenancy row-level, RBAC fail-closed `modulo:accion`, flujo Router→Service→Repository→Model, Pydantic `extra='forbid'`, ≤500 LOC backend / <200 LOC componentes React, sin `max-w-*`/`mx-auto` en wrapper raíz de página.

## Goals / Non-Goals

**Goals:**
- Exponer un endpoint read-only `GET /api/v1/alumno/estado-academico` que devuelva el estado académico del alumno autenticado: materias inscriptas, calificaciones propias, estado de entregas, porcentaje de avance y coloquios reservados.
- Garantizar que un alumno SÓLO ve sus propios datos, derivando identidad y tenant exclusivamente del JWT.
- Entregar la pantalla `/mi-cursada` exclusiva del rol ALUMNO, integrada al shell con un grupo de nav `MI CURSADA`.
- Reusar los componentes del design system (`Card`, `KpiCard`, `PageHeader`, `EmptyState`, `TableWrapper`, `StatusBadge`).

**Non-Goals:**
- NO se implementa la reserva de coloquios (HU-47): el endpoint de reserva ya existe (C-14); este portal sólo **muestra** las reservas activas.
- NO se modifica el modelo de datos ni se crean migraciones (read-only).
- NO se crea/edita el permiso `academico:ver_propio` (ya existe en el RBAC).
- NO se cubre la edición de perfil del alumno (fuera de alcance; perfil docente es C-20).
- NO se resuelve PA-01/PA-07 (catálogo de materias / cohortes ↔ carrera): el portal consume lo que el padrón ya enlaza, sin tocar estructura académica.

## Decisions

### D1 — El vínculo alumno↔datos es `EntradaPadron.usuario_id`, resuelto en el repository
El repository parte de `current_user.user_id` y busca todas las `EntradaPadron` (no soft-deleted) cuyo `usuario_id == user_id` **y** `tenant_id == tenant_id`. De esas entradas derivan materias y calificaciones. Las reservas de coloquio se obtienen por la vía directa `ReservaEvaluacion.alumno_id == user_id`.
- **Alternativa descartada**: cruzar por email (`EntradaPadron.email_encrypted`). Se descarta porque el email está cifrado no-determinístico (sin blind index en el padrón, D3 de C-09) — no es consultable por igualdad. El FK `usuario_id` es el enlace correcto y ya está modelado.
- **Consecuencia**: si una `EntradaPadron` del alumno aún no tiene `usuario_id` reconciliado, esa materia no aparece. Es el comportamiento correcto y seguro (fail-closed); se documenta como nota.

### D2 — `materia_id` se toma desde `Calificacion` y `VersionPadron`, no se infiere
La lista de materias del alumno = unión de `version.materia_id` de sus `EntradaPadron` activas. El nombre de la materia se resuelve por join a `Materia`. El avance por materia se calcula sobre las `Calificacion` de esa `entrada_padron`.

### D3 — Porcentaje de avance: derivado en query, nunca persistido
`avance_pct` por materia = `aprobadas / total_actividades * 100` (redondeado), donde `total_actividades` es el conteo de `Calificacion` del alumno en esa materia y `aprobadas` el conteo con `aprobado = true`. El avance global es el promedio ponderado por cantidad de actividades. Si el alumno no tiene calificaciones en la materia, `avance_pct = 0` y `total_actividades = 0`.
- **Alternativa descartada**: usar `UmbralMateria` para recalcular `aprobado` en el portal. Se descarta: `aprobado` ya viene persistido y derivado al importar (D3 de C-10); recalcular duplicaría lógica. El portal confía en el dato persistido.

### D4 — Estado de entrega por actividad: enum derivado de `aprobado` + presencia de nota
Cada `Calificacion` se clasifica para la UI: `aprobada` (`aprobado=true`), `con_nota` (tiene `nota_numerica` o `nota_textual` pero `aprobado=false`), `sin_entrega` (ambos nulos). Esta clasificación se computa en el Service (lógica de presentación pura), no en el repository.

### D5 — Un único endpoint agregado, no varios granulares
Se expone `GET /api/v1/alumno/estado-academico` que devuelve el objeto completo (`materias[]` con `calificaciones[]` embebidas + `coloquios_reservados[]` + KPIs globales). Evita N+1 desde el frontend y un round-trip por sección.
- **Alternativa descartada**: endpoints separados (`/alumno/materias`, `/alumno/coloquios`). Se descarta por simplicidad de la pantalla única `/mi-cursada` y para minimizar superficie de API. Si crece, se podrá granularizar luego.

### D6 — Repository dedicado `AlumnoRepository`, sin reusar repos de otros módulos
Aunque consulta tablas de C-09/C-10/C-14, las queries del portal son específicas (scope por `usuario_id`, joins agregados). Se crea `AlumnoRepository(TenantScopedRepository)` con métodos read-only. Mantiene la regla "queries SOLO en repositories" y no contamina los repos existentes con casos de uso del alumno.

### D7 — Frontend: feature `mi-cursada` con gating doble (ruta + nav)
- `App.tsx`: ruta `/mi-cursada` envuelta en `ProtectedRoute requiredRoles={['ALUMNO']}`.
- `buildNav.ts`: ítem `Mi cursada` (`path: '/mi-cursada'`, `roles: ['ALUMNO']`, `group: 'MI CURSADA'`).
- La página vuelve a verificar el rol con `useAuth` y muestra acceso denegado si no es ALUMNO (defensa en profundidad, igual patrón que `ColoquiosPage`).
- Fetch vía hook TanStack Query (`useEstadoAcademico`) que pega al cliente Axios centralizado.

### D8 — DTOs Pydantic `extra='forbid'`, Read-only, `from_attributes` donde mapeen ORM
Schemas de respuesta sin campos de identidad en request (no hay request body — es un GET sin params). El endpoint no recibe `alumno_id` por ninguna vía.

## Risks / Trade-offs

- **[Alumno sin `usuario_id` reconciliado en el padrón]** → sus materias no aparecen. Mitigación: documentar el supuesto; es el comportamiento seguro. La reconciliación padrón↔cuenta es responsabilidad de C-09/onboarding, fuera de este change.
- **[Performance: joins agregados sobre calificaciones]** → con muchos alumnos/actividades podría ser costoso. Mitigación: las queries van scopeadas por `usuario_id` + `tenant_id` (índices existentes en `entrada_padron.usuario_id`, `calificacion.entrada_padron_id`, `reserva_evaluacion.alumno_id`); el volumen por alumno es acotado. Sin N+1: agregaciones en SQL.
- **[Doble fuente de verdad del avance si cambia la definición de `aprobado`]** → el portal confía en `Calificacion.aprobado` persistido. Mitigación: explícitamente NO recalcula; cualquier cambio de criterio se refleja al re-importar (regla de C-10).
- **[Multi-rol ALUMNO+otro]** → un usuario que sea ALUMNO y además PROFESOR vería el ítem de nav y la ruta. Mitigación: aceptado — el endpoint igualmente sólo devuelve datos donde el padrón lo enlaza como alumno; no hay fuga de datos de otros.

## Migration Plan

No aplica migración de base de datos (change read-only). Despliegue aditivo:
1. Backend: agregar router/service/repo/schema y registrar el router en `routers/__init__.py`.
2. Frontend: agregar feature, ruta y entrada de nav.
3. Rollback: revertir el commit; al ser aditivo y read-only no deja estado persistente que limpiar.

## Open Questions

- **OQ-1**: ¿El "porcentaje de avance" institucionalmente se define sobre TODAS las actividades del padrón/programa o sólo sobre las calificaciones cargadas? Decisión tomada para este change: sobre las calificaciones cargadas del alumno (lo único consultable hoy). Si el negocio exige avance contra el total del programa, requerirá datos de programa por materia (no disponibles como conteo hoy) — se deja como mejora futura.
- **OQ-2**: ¿Se muestran coloquios reservados de cualquier `tipo` de evaluación o sólo `Coloquio`? Decisión: mostrar todas las reservas `Activa` del alumno (cualquier `EvaluacionTipo`), etiquetando el tipo; el alumno reserva turnos de evaluación en general. Ajustable si se quiere acotar a `Coloquio`.
