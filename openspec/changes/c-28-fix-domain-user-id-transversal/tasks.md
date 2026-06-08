# Tasks — c-28-fix-domain-user-id-transversal

> Strict TDD por task de fix: safety-net (correr tests del módulo antes de tocar) → RED → GREEN → triangulación (IDs distintos: `auth_identity_id != usuario.id`) → refactor. Sin mocks de DB (regla dura #4). Governance ALTO: cada fix con test de regresión.

## 1. Auditoría y congelamiento del alcance

- [ ] 1.1 Grep transversal en `backend/app/api/v1/routers/` y `backend/app/services/` de `current_user.user_id` y de nombres de columna FK de dominio (`cargado_por`, `importado_por`, `asignado_por`, `enviado_por`, `aprobado_por`, `autor_id`, `usuario_id=`).
- [ ] 1.2 Clasificar cada hit en: (a) correcto, (b) bug de dominio, (c) excepción de auditoría. Cruzar cada columna sospechosa contra su modelo para confirmar si es FK a `usuario.id`.
- [ ] 1.3 Revisar módulos no listados en el proposal (`inbox.py`, `programas.py`, `fechas_academicas.py`, `encuentros.py`, `guardias.py`, `coloquios.py`, `equipos.py`, `padron.py`, `analisis.py`, `alumno.py`) por escrituras/filtros de FK de dominio vía `current_user.user_id`.
- [ ] 1.4 Confirmar que `auth.py` (identity repo) y `audit.actor_user_id` quedan FUERA de alcance (excepción documentada).

## 2. Fix avisos — feed y pendientes

- [ ] 2.1 Safety-net: correr tests existentes de avisos; capturar baseline.
- [ ] 2.2 RED: test que verifica que `listar_feed`/`listar_pendientes` marcan ack contra `usuario.id` (fixture con `auth_identity_id != usuario.id`).
- [ ] 2.3 GREEN: en `routers/avisos.py` resolver `domain_user_id` y pasarlo como `usuario_id` a `listar_feed`/`listar_pendientes` (líneas ~155, ~182). Ajustar firma del service si hace falta.
- [ ] 2.4 Triangulación: caso con ack existente vs. sin ack; confirmar estado leído/no-leído correcto.

## 3. Fix encuentros — listado por asignación del actor

- [ ] 3.1 Safety-net: correr tests de encuentros; baseline.
- [ ] 3.2 RED: test que `encuentro_service` filtra asignaciones del actor por `usuario.id`, no `auth_identity_id`.
- [ ] 3.3 GREEN: resolver `domain_user_id` en `routers/encuentros.py` y propagarlo; reemplazar `_asig_repo.list(usuario_id=current_user.user_id)` (`encuentro_service.py:232,258`) por `usuario_id=domain_user_id`.
- [ ] 3.4 Triangulación: actor con asignaciones vs. sin asignaciones.

## 4. Fix guardias — listado por asignación del actor

- [ ] 4.1 Safety-net: correr tests de guardias; baseline.
- [ ] 4.2 RED: test que `guardia_service` filtra por `usuario.id`.
- [ ] 4.3 GREEN: resolver `domain_user_id` en `routers/guardias.py` y propagarlo; reemplazar `_asig_repo.list(usuario_id=current_user.user_id)` (`guardia_service.py:107,186`).
- [ ] 4.4 Triangulación: dos actores con distintas asignaciones; confirmar aislamiento.

## 5. Fix padron — ownership check

- [ ] 5.1 Safety-net: correr tests de padron; baseline.
- [ ] 5.2 RED: test que PROFESOR (sin `gestionar`) solo puede vaciar su propia versión, comparando `cargado_por` contra `usuario.id`.
- [ ] 5.3 GREEN: en `padron_service.py:179` comparar `version.cargado_por` contra `domain_user_id` (resuelto en el router), no `current_user.user_id`.
- [ ] 5.4 Triangulación: dueño puede vaciar; no-dueño recibe 403.

## 6. Endurecer fallbacks de services (eliminar `domain_user_id or current_user.user_id`)

- [ ] 6.1 Safety-net: correr la suite de cada service afectado; baseline.
- [ ] 6.2 RED: test que falla si se llama el método sin `domain_user_id` (firma requerida).
- [ ] 6.3 GREEN: `calificacion_service.py:224`, `equipo_service.py:77`, `padron_service.py:114`, `alumno_service.py:89` y los `else current_user.user_id` de `analisis_service.py` → `domain_user_id: uuid.UUID` requerido, sin fallback. Confirmar que los routers ya pasan `domain_user_id` siempre.
- [ ] 6.4 Triangulación: filtro de scope `propio` matchea registros del actor con `auth_identity_id != usuario.id`.

## 7. Documentación del invariante

- [ ] 7.1 Agregar a `docs/ARQUITECTURA.md` sección "Identidad: dominio vs. auth": tabla `usuario.id` (FKs de dominio) vs `auth_identities.id` (identidad/auditoría), snippet de `resolve_domain_user_id`, y la excepción de `audit.actor_user_id`.
- [ ] 7.2 Referenciar el invariante en `CLAUDE.md` (regla dura adicional / nota en sección de seguridad) para que sea lo primero que lee un agente.

## 8. Verificación global y cierre

- [ ] 8.1 Correr la suite backend completa; confirmar verde (cobertura ≥80% líneas, ≥90% reglas de negocio).
- [ ] 8.2 Grep de cierre: 0 usos de `current_user.user_id` en columnas FK a `usuario.id` fuera de la excepción de auditoría documentada.
- [ ] 8.3 Actualizar `Estado` del change en `CHANGES.md` si aplica.
