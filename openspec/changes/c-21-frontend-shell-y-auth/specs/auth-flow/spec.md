## ADDED Requirements

### Requirement: Inicio de sesión con email y contraseña

El frontend SHALL ofrecer una página de login pública (accesible sin sesión) que solicite email y contraseña, valide el formato con Zod antes de enviar, y autentique al usuario contra `POST /api/v1/auth/login`. El email es el único identificador de acceso; nunca se acepta legajo ni identificador numérico.

#### Scenario: Login exitoso con credenciales válidas
- **WHEN** un usuario no autenticado envía un email con formato válido y una contraseña correcta desde la página de login
- **THEN** el sistema almacena el access token recibido en memoria, hidrata la sesión (`user`, `roles`, `tenantId`) desde la respuesta del backend, y redirige al layout principal de la aplicación

#### Scenario: Login con credenciales inválidas
- **WHEN** el usuario envía credenciales que el backend rechaza con `401`
- **THEN** el sistema muestra un mensaje de error genérico ("Email o contraseña incorrectos"), no almacena ningún token, y mantiene al usuario en la página de login

#### Scenario: Validación de formato antes de enviar
- **WHEN** el usuario intenta enviar el formulario con un email de formato inválido o un campo vacío
- **THEN** el formulario muestra el error de validación de Zod en el campo correspondiente y no realiza la petición al backend

### Requirement: Almacenamiento del access token en memoria

El frontend SHALL mantener el access token exclusivamente en memoria del proceso (estado de la aplicación), nunca en `localStorage` ni `sessionStorage`. El refresh token SHALL ser gestionado por el backend mediante cookie httpOnly y nunca es leído ni escrito por código JavaScript.

#### Scenario: El access token no se persiste en almacenamiento del navegador
- **WHEN** el usuario inicia sesión correctamente
- **THEN** el access token queda disponible solo en memoria de la aplicación y no aparece en `localStorage` ni en `sessionStorage`

#### Scenario: Recarga de página sin token en memoria
- **WHEN** el usuario recarga la página y el access token en memoria se pierde
- **THEN** el sistema intenta rehidratar la sesión vía refresh (cookie httpOnly); si el refresh es válido obtiene un nuevo access token, y si falla redirige a la página de login

### Requirement: Cliente HTTP centralizado con adjunto de token

El frontend SHALL exponer una única instancia de Axios en `shared/services/api.ts` por la que pasa todo fetch al backend. Un interceptor de request SHALL adjuntar el access token vigente como header `Authorization: Bearer <token>` en cada petición autenticada.

#### Scenario: Petición autenticada adjunta el token
- **WHEN** se realiza una petición al backend con una sesión activa
- **THEN** el interceptor de request agrega el header `Authorization: Bearer <access_token>` antes de enviar la petición

#### Scenario: Petición sin sesión no adjunta token
- **WHEN** se realiza una petición (por ejemplo, el login) sin access token en memoria
- **THEN** el interceptor no agrega el header `Authorization` y la petición se envía sin él

### Requirement: Refresh automático con rotación ante 401

El interceptor de response del cliente HTTP SHALL detectar respuestas `401` por token expirado, disparar `POST /api/v1/auth/refresh` (que rota el refresh token), reintentar la petición original UNA sola vez con el nuevo access token, y serializar refrescos concurrentes para no disparar múltiples refresh simultáneos.

#### Scenario: Refresh exitoso y reintento de la petición
- **WHEN** una petición autenticada recibe `401` por access token expirado y el refresh token (cookie httpOnly) sigue siendo válido
- **THEN** el sistema obtiene un nuevo access token vía refresh, lo guarda en memoria, y reintenta la petición original que ahora responde correctamente

#### Scenario: Refresh fallido fuerza logout
- **WHEN** el refresh falla (refresh token vencido, revocado o ausente)
- **THEN** el sistema limpia la sesión en memoria y redirige al usuario a la página de login

#### Scenario: Peticiones concurrentes comparten un solo refresh
- **WHEN** varias peticiones reciben `401` casi simultáneamente
- **THEN** el sistema dispara un único refresh, encola las peticiones afectadas y las reintenta a todas con el nuevo token, sin disparar refrescos duplicados

#### Scenario: El reintento no entra en bucle
- **WHEN** una petición ya reintentada tras un refresh vuelve a recibir `401`
- **THEN** el sistema no dispara otro refresh para esa petición, limpia la sesión y redirige a login

### Requirement: Estado de sesión expuesto por useAuth

El frontend SHALL exponer un hook `useAuth` (respaldado por un `AuthProvider`) que provea `user`, `roles`, `tenantId`, `isAuthenticated`, `login()` y `logout()`. La identidad, los roles y el tenant SHALL derivarse exclusivamente de la respuesta del backend (token verificado / endpoint de identidad), nunca de datos manipulables por el cliente.

#### Scenario: La sesión refleja la identidad del backend
- **WHEN** un componente consume `useAuth` con una sesión activa
- **THEN** `user`, `roles` y `tenantId` reflejan los valores provistos por el backend e `isAuthenticated` es `true`

#### Scenario: Sin sesión el hook reporta no autenticado
- **WHEN** no existe sesión activa
- **THEN** `isAuthenticated` es `false`, `user` es `null` y `roles` es una lista vacía

### Requirement: Cierre de sesión

El frontend SHALL ofrecer una acción de logout que invoque `POST /api/v1/auth/logout` para revocar la sesión en el servidor, descarte el access token en memoria, limpie el estado de sesión y de la caché de servidor, y redirija al usuario a la página de login.

#### Scenario: Logout revoca y redirige
- **WHEN** un usuario autenticado ejecuta la acción de cerrar sesión
- **THEN** el sistema invoca el endpoint de logout, descarta el access token en memoria, limpia el estado de `useAuth` y la caché de TanStack Query, y redirige a la página de login

#### Scenario: Logout resiliente a fallo del backend
- **WHEN** la llamada al endpoint de logout falla por error de red
- **THEN** el sistema igualmente limpia la sesión local y redirige a login, para no dejar al usuario en un estado autenticado en el cliente
