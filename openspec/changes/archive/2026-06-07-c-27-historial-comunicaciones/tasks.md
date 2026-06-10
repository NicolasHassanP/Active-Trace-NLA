## 1. Migración Alembic — Índice de historial

- [x] 1.1 Crear migración Alembic para el índice compuesto `ix_comunicacion_tenant_enviado_por_created` en `(tenant_id, enviado_por, created_at DESC)` sobre la tabla `comunicacion`
- [x] 1.2 Verificar que la migración corre sin errores en la base de datos de test (`alembic upgrade head`)

## 2. Backend — Repositorio

- [x] 2.1 Escribir test unitario RED para `ComunicacionRepository.list_by_sender`: verifica que retorna solo las comunicaciones del sender en el tenant, respetando `deleted_at`
- [x] 2.2 Implementar `list_by_sender(sender_id, estado?, offset, limit) -> (List[Comunicacion], int)` en `backend/app/repositories/comunicacion_repository.py`
- [x] 2.3 Agregar test de triangulación: filtro por estado retorna solo comunicaciones con ese estado
- [x] 2.4 Agregar test de triangulación: paginación retorna `total` correcto y `items` con tamaño `limit`
- [x] 2.5 Verificar tests en GREEN (`pytest backend/tests/... -k list_by_sender`)

## 3. Backend — Schema

- [x] 3.1 Escribir test RED para `MisEnviosResponse`: verifica validación Pydantic con `extra='forbid'` y campos `total`, `offset`, `limit`, `items`
- [x] 3.2 Agregar `MisEnviosResponse` a `backend/app/schemas/comunicacion.py` (Pydantic v2, `extra='forbid'`)
- [x] 3.3 Verificar tests en GREEN

## 4. Backend — Endpoint

- [x] 4.1 Escribir test de integración RED para `GET /comunicaciones/mis-envios`: responde 200 con `MisEnviosResponse`, aislado por tenant y por sender
- [x] 4.2 Agregar endpoint `GET /comunicaciones/mis-envios` en `backend/app/api/v1/routers/comunicaciones.py` con query params `estado`, `offset`, `limit`; identidad desde `resolve_domain_user_id()`; permiso `comunicacion:enviar`
- [x] 4.3 Agregar test de triangulación: usuario sin permiso recibe 403
- [x] 4.4 Agregar test de triangulación: filtro por estado retorna solo las comunicaciones en ese estado
- [x] 4.5 Agregar test de triangulación: usuario sin envíos propios recibe `total=0, items=[]`
- [x] 4.6 Verificar todos los tests de integración del endpoint en GREEN

## 5. Frontend — Service y Hook

- [x] 5.1 Definir el tipo `MisEnviosParams` y `MisEnviosResponse` en `frontend/src/features/comunicaciones/types/index.ts`
- [x] 5.2 Agregar `getMisEnvios(params: MisEnviosParams)` en `frontend/src/features/comunicaciones/services/comunicacionService.ts`
- [x] 5.3 Agregar `useMisEnvios(params: MisEnviosParams)` en `frontend/src/features/comunicaciones/hooks/comunicacionHooks.ts` usando `useQuery` con `queryKey: ['mis-envios', params]`
- [x] 5.4 Agregar tests unitarios para `getMisEnvios` (mock de `apiClient`) y `useMisEnvios` (mock de `getLote`)

## 6. Frontend — Componente ComunicacionesHistorial

- [x] 6.1 Crear `frontend/src/features/comunicaciones/components/ComunicacionesHistorial.tsx`: tabla con columnas asunto, estado (badge), destinatario, fecha; select de filtro de estado; paginación Anterior/Siguiente usando `useMisEnvios`
- [x] 6.2 Manejar estados de carga (spinner/skeleton), error (mensaje descriptivo) y vacío ("No tenés envíos todavía")
- [x] 6.3 Agregar tests del componente: verifica render de tabla, filtro actualiza query key, paginación deshabilita "Siguiente" al llegar al final, estado vacío

## 7. Frontend — Actualizar ComunicacionesPage

- [x] 7.1 Agregar estado `activeTab: 'componer' | 'historial'` con default `'componer'` en `ComunicacionesPage.tsx`
- [x] 7.2 Agregar UI de tabs (botones o tab bar Tailwind) "Componer" e "Historial"
- [x] 7.3 Renderizar `ComunicacionesHistorial` solo cuando `activeTab === 'historial'`
- [x] 7.4 Preservar comportamiento actual de Componer + bandeja de lote activo en la tab "Componer"
- [x] 7.5 Actualizar tests de `ComunicacionesPage.test.tsx`: verifica que por defecto muestra la tab Componer, que al cambiar a Historial monta `ComunicacionesHistorial`, y que al volver a Componer el formulario sigue disponible

## 8. Verificación final

- [x] 8.1 Ejecutar suite completa de tests de comunicaciones backend (`pytest backend/tests/ -k comunicacion`)
- [x] 8.2 Ejecutar suite completa de tests de comunicaciones frontend (`npm test -- --testPathPattern=comunicacion`)
- [x] 8.3 Verificar que la cobertura de líneas del módulo `comunicacion` se mantiene ≥80% y reglas de negocio ≥90%
