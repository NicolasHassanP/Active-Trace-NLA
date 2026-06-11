## ADDED Requirements

### Requirement: Tab "Historial" en ComunicacionesPage
La aplicación SHALL agregar navegación por tabs en `/comunicaciones` con dos opciones: "Componer" (comportamiento actual) e "Historial". La tab activa SHALL gestionarse con estado local (`useState`). Al cambiar a la tab "Historial", el componente `ComunicacionesHistorial` SHALL montarse. Al cambiar de vuelta a "Componer", el formulario de composición y la bandeja de lote activo SHALL seguir disponibles. La tab por defecto SHALL ser "Componer".

#### Scenario: Por defecto se muestra la tab Componer
- **WHEN** el usuario navega a `/comunicaciones`
- **THEN** la tab "Componer" está activa y el formulario de composición es visible
- **AND** el componente ComunicacionesHistorial NO está montado

#### Scenario: Clic en tab Historial monta el componente de historial
- **WHEN** el usuario hace clic en la tab "Historial"
- **THEN** `ComunicacionesHistorial` se monta y consulta `GET /comunicaciones/mis-envios`
- **AND** el formulario de composición deja de ser visible

#### Scenario: Clic en tab Componer restaura la vista de composición
- **WHEN** el usuario estaba en la tab "Historial" y hace clic en "Componer"
- **THEN** el formulario de composición es visible nuevamente
- **AND** el `loteId` activo (si existe) sigue disponible para mostrar la bandeja de estado

### Requirement: Componente ComunicacionesHistorial
La aplicación SHALL proveer el componente `ComunicacionesHistorial` que liste las comunicaciones propias del usuario autenticado consumiendo `GET /api/v1/comunicaciones/mis-envios` vía TanStack Query. El componente SHALL ofrecer un select de filtro de estado con opciones: "Todos", "Pendiente", "Enviando", "Enviado", "Error", "Cancelado". El componente SHALL mostrar una tabla/lista con columnas: asunto, estado (badge de color), destinatario, fecha de envío (`creado_en`). El componente SHALL implementar paginación con botones "Anterior" / "Siguiente" usando `offset` / `limit`. El componente SHALL mostrar un estado de carga (`loading`) y un estado de error con mensaje descriptivo.

#### Scenario: Lista el historial de envíos al montar
- **WHEN** el componente se monta
- **THEN** realiza `GET /comunicaciones/mis-envios?offset=0&limit=20`
- **AND** muestra los items retornados en una tabla

#### Scenario: Filtro por estado actualiza la consulta
- **WHEN** el usuario selecciona "Enviado" en el select de estado
- **THEN** el componente realiza `GET /comunicaciones/mis-envios?estado=Enviado&offset=0&limit=20`
- **AND** la tabla muestra solo items con estado "Enviado"

#### Scenario: Paginación avanza al siguiente bloque
- **WHEN** el usuario hace clic en "Siguiente" y existen más items
- **THEN** el componente realiza `GET /comunicaciones/mis-envios?offset=20&limit=20`
- **AND** la tabla muestra los items de la segunda página

#### Scenario: Paginación no avanza cuando no hay más items
- **WHEN** `offset + limit >= total`
- **THEN** el botón "Siguiente" está deshabilitado

#### Scenario: Estado vacío cuando no hay envíos
- **WHEN** la API retorna `{"total": 0, "items": []}`
- **THEN** el componente muestra un mensaje "No tenés envíos todavía" o similar

#### Scenario: Error de red muestra mensaje descriptivo
- **WHEN** la petición a `GET /comunicaciones/mis-envios` falla con error de red
- **THEN** el componente muestra un mensaje de error descriptivo sin romper la página

### Requirement: Hook useMisEnvios y función getMisEnvios en el service
La aplicación SHALL proveer la función `getMisEnvios(params: MisEnviosParams)` en `comunicacionService.ts` que hace `GET /comunicaciones/mis-envios` con los query params serializados. La aplicación SHALL proveer el hook `useMisEnvios(params: MisEnviosParams)` en `comunicacionHooks.ts` usando `useQuery` de TanStack Query con `queryKey: ['mis-envios', params]`. El hook SHALL invalidar la query cuando cambie cualquier campo de `params`.

#### Scenario: Hook retorna los datos cuando la petición es exitosa
- **WHEN** `useMisEnvios({ offset: 0, limit: 20 })` es invocado y la API responde 200
- **THEN** `data` contiene `{ total, offset, limit, items }`

#### Scenario: Cambio de filtro invalida y refetch la query
- **WHEN** el estado del filtro cambia de `undefined` a `"Enviado"`
- **THEN** el hook realiza un nuevo fetch con `?estado=Enviado`
- **AND** los datos anteriores son reemplazados por los nuevos
