> **Modo Strict TDD**: para cada tarea de lógica, seguir RED → GREEN → TRIANGULATE → REFACTOR.
> Antes de modificar archivos existentes (router de usuarios, catálogo RBAC), correr la red de seguridad (tests previos en verde) y reportar el baseline.
> Tests sin mocks de DB: usar base efímera / contenedor de test.

## 1. Preparación y red de seguridad

- [ ] 1.1 Correr la suite de `usuarios` (C-07) y del catálogo RBAC; capturar baseline "N tests passing" antes de tocar nada compartido
- [ ] 1.2 Confirmar contra el modelo real de `Usuario` (C-07) si existe la columna `genero`/`sexo` y la lista exacta de campos PII (resuelve OQ-2); documentar el hallazgo
- [ ] 1.3 Registrar los permisos `perfil:editar` e `inbox:usar` en el catálogo RBAC (administrable como datos) y su asignación a roles por defecto (perfil: todo usuario autenticado; inbox: TUTOR/PROFESOR/COORDINADOR/ADMIN) — resuelve OQ-1

## 2. Schemas de perfil (Pydantic v2, extra='forbid')

- [ ] 2.1 RED: test de `PerfilUpdate` que falle al incluir `cuil` (422) y al incluir campos no declarados (`tenant_id`, `estado`)
- [ ] 2.2 GREEN: implementar `PerfilUpdate` con solo los campos editables (nombre, apellidos, dni, genero, banco, cbu, alias_cbu, regional, email, facturador, legajo_profesional), `extra='forbid'`, sin `cuil`
- [ ] 2.3 TRIANGULATE: casos de validación adicionales (campos opcionales/parciales en el PATCH; `cuerpo`/strings vacíos donde aplique) → al menos happy path + edge
- [ ] 2.4 RED→GREEN: `PerfilRead` que incluya `cuil` solo-lectura y devuelva PII del dueño en claro; test de su forma
- [ ] 2.5 REFACTOR: limpiar duplicación entre `PerfilRead`/`PerfilUpdate` y los schemas de `usuarios`; mantener <500 LOC por archivo

## 3. Repositorio de perfil (scope por tenant)

- [ ] 3.1 RED: test de `get_self(tenant_id, usuario_id)` que NO devuelva usuarios de otro tenant (aislamiento) ni con `id` colisionante entre tenants
- [ ] 3.2 GREEN: método de lectura scoped por `tenant_id` reusando el repo/modelo de `Usuario`
- [ ] 3.3 RED: test de `update_self` que persista campos editables y mantenga PII cifrada en reposo (AES-256, valor en DB ≠ texto plano)
- [ ] 3.4 GREEN: implementar `update_self` (solo campos editables) con cifrado PII reusando el de `usuarios`
- [ ] 3.5 TRIANGULATE: actualización de `email` recalcula `email_hash`; unicidad `(tenant_id, email)` rechazada (409) y email libre aceptado
- [ ] 3.6 REFACTOR: queries solo en el repository; sin SQL en service

## 4. Servicio de perfil

- [ ] 4.1 RED: test de servicio `obtener_perfil` que use el `usuario_id` del JWT y nunca un id de la petición
- [ ] 4.2 GREEN: implementar `obtener_perfil`
- [ ] 4.3 RED: test de `actualizar_perfil` que rechace conflicto de email (409) y registre evento de auditoría sin PII en texto plano
- [ ] 4.4 GREEN: implementar `actualizar_perfil` con la regla de unicidad y la auditoría
- [ ] 4.5 TRIANGULATE: edición exitosa de campos PII + edición sin cambios + intento de cambiar identidad (ignorado)
- [ ] 4.6 REFACTOR: extraer helpers, asegurar que la PII no aparezca en logs

## 5. Router de perfil (/api/v1/perfil)

- [ ] 5.1 RED: test e2e `GET /api/v1/perfil` 401 sin JWT y 200 con JWT devolviendo el perfil del titular
- [ ] 5.2 GREEN: implementar `GET /api/v1/perfil` con identidad del JWT (ignora `usuario_id` de la query)
- [ ] 5.3 RED: test e2e `PATCH /api/v1/perfil` → 403 sin `perfil:editar`, 422 con campo prohibido, 409 email duplicado, 200 happy path
- [ ] 5.4 GREEN: implementar `PATCH /api/v1/perfil` con `require_permission("perfil:editar")`
- [ ] 5.5 TRIANGULATE: intento de editar el perfil de otro (id en body) → ignorado; intento de editar `cuil` → 422
- [ ] 5.6 REFACTOR: sin lógica de negocio en el router; flujo Router → Service → Repository

## 6. Modelos y migración de mensajería

- [ ] 6.1 RED: test de modelos `HiloMensaje`, `Mensaje`, `HiloParticipante` (campos, `tenant_id`, `deleted_at`, FKs, `remitente_id`)
- [ ] 6.2 GREEN: implementar los modelos SQLAlchemy 2.0 async con `tenant_id` y soft delete
- [ ] 6.3 GREEN: una migración Alembic que cree las 3 tablas con índices de aislamiento `(tenant_id, usuario_id)` en participantes y `(tenant_id, hilo_id, created_at)` en mensajes
- [ ] 6.4 TRIANGULATE: test que verifique que la migración aplica y revierte (drop) sin tocar tablas existentes

## 7. Schemas de mensajería (Pydantic v2, extra='forbid')

- [ ] 7.1 RED: tests de `MensajeCreate`/`HiloCreate`/`RespuestaCreate` que rechacen `cuerpo` vacío (422) y campos no declarados (`remitente_id`, `tenant_id`)
- [ ] 7.2 GREEN: implementar los schemas con `asunto`/`cuerpo` requeridos, `extra='forbid'`, destinatarios en `HiloCreate`
- [ ] 7.3 RED→GREEN: schemas de lectura `InboxHiloRead` (con conteo de no leídos) y `MensajeRead`
- [ ] 7.4 REFACTOR: deduplicar; mantener <500 LOC por archivo

## 8. Repositorio de mensajería (aislamiento usuario × tenant)

- [ ] 8.1 RED: test `listar_hilos(tenant_id, usuario_id)` que solo devuelva hilos donde el usuario participa, ordenados por actividad, con no-leídos
- [ ] 8.2 GREEN: implementar `listar_hilos` con JOIN a participantes scoped por tenant
- [ ] 8.3 RED: test `obtener_hilo` que devuelva 404-equivalente para no participante y para hilo de otro tenant
- [ ] 8.4 GREEN: implementar `obtener_hilo` + mensajes en orden cronológico (excluyendo soft-deleted)
- [ ] 8.5 RED: test `agregar_mensaje`/`crear_hilo` que persistan con `remitente_id` y `tenant_id` correctos
- [ ] 8.6 GREEN: implementar escritura de mensaje/hilo + participantes
- [ ] 8.7 RED: test de `marcar_leido` (actualiza `last_read_at`) y cálculo de no-leídos por participante
- [ ] 8.8 GREEN: implementar marcado de leído y conteo de no-leídos
- [ ] 8.9 TRIANGULATE: aislamiento entre dos usuarios del mismo tenant + aislamiento cross-tenant + soft delete excluye de listados activos
- [ ] 8.10 REFACTOR: queries solo en repository

## 9. Servicio de mensajería

- [ ] 9.1 RED: test `ver_inbox` que use el `usuario_id` del JWT y devuelva solo hilos propios con no-leídos
- [ ] 9.2 GREEN: implementar `ver_inbox`
- [ ] 9.3 RED: test `abrir_hilo` que marque leído al abrir y rechace no participante / cross-tenant
- [ ] 9.4 GREEN: implementar `abrir_hilo`
- [ ] 9.5 RED: test `responder` que ignore `remitente_id` del body (anti-spoofing) y rechace a no participantes
- [ ] 9.6 GREEN: implementar `responder` atribuyendo remitente desde el JWT
- [ ] 9.7 RED: test `iniciar_hilo` que rechace destinatario de otro tenant y cree hilo + primer mensaje
- [ ] 9.8 GREEN: implementar `iniciar_hilo`
- [ ] 9.9 TRIANGULATE: múltiples mensajes en un hilo + conteo de no-leídos tras nueva respuesta + 1:1 vs grupal (según OQ-3)
- [ ] 9.10 REFACTOR: dividir el service si supera 500 LOC (listar / abrir / responder / iniciar)

## 10. Router de mensajería (/api/v1/inbox)

- [ ] 10.1 RED: test e2e `GET /api/v1/inbox` → 403 sin `inbox:usar`, 200 con solo hilos propios y conteo de no-leídos
- [ ] 10.2 GREEN: implementar `GET /api/v1/inbox` con `require_permission("inbox:usar")`
- [ ] 10.3 RED: test e2e `GET /api/v1/inbox/{hilo_id}` → 200 participante (marca leído), 404 no participante, 404 cross-tenant
- [ ] 10.4 GREEN: implementar `GET /api/v1/inbox/{hilo_id}`
- [ ] 10.5 RED: test e2e `POST /api/v1/inbox/{hilo_id}/responder` → 201 participante, 404 no participante, 422 cuerpo vacío / campo prohibido
- [ ] 10.6 GREEN: implementar `POST /api/v1/inbox/{hilo_id}/responder`
- [ ] 10.7 RED: test e2e `POST /api/v1/inbox` → 201 con destinatario del tenant, 404/422 con destinatario de otro tenant
- [ ] 10.8 GREEN: implementar `POST /api/v1/inbox`
- [ ] 10.9 TRIANGULATE: anti-spoofing de `remitente_id` en endpoints de escritura; paginación de inbox/hilo
- [ ] 10.10 REFACTOR: sin lógica de negocio en el router; flujo Router → Service → Repository

## 11. Wiring, cobertura y cierre

- [ ] 11.1 Registrar los routers `perfil` e `inbox` en la app FastAPI
- [ ] 11.2 Verificar cobertura ≥80% líneas y ≥90% en reglas de negocio (aislamiento, anti-spoofing, unicidad email, cuil read-only)
- [ ] 11.3 Verificar que ninguna PII (`dni`, `cuil`, `cbu`, `alias_cbu`) aparece en logs en ningún flujo (test transversal)
- [ ] 11.4 Re-correr la red de seguridad de C-07/RBAC y confirmar que sigue en verde (no se rompió nada)
- [ ] 11.5 Reportar la tabla de evidencia TDD (Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR)
