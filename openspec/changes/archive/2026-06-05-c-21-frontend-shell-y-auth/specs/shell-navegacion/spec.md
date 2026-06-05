## ADDED Requirements

### Requirement: Guard de rutas autenticadas

El frontend SHALL proteger toda ruta privada con un componente `ProtectedRoute` que verifique la sesión antes de renderizar. Una ruta privada accedida sin sesión válida SHALL redirigir a `/login`, preservando la ruta de destino para retomarla tras un login exitoso.

#### Scenario: Acceso autenticado a ruta privada
- **WHEN** un usuario autenticado navega a una ruta protegida
- **THEN** `ProtectedRoute` renderiza el contenido de la ruta

#### Scenario: Acceso no autenticado a ruta privada
- **WHEN** un usuario sin sesión válida intenta acceder a una ruta protegida
- **THEN** el sistema lo redirige a `/login` y conserva la ruta solicitada para redirigirlo allí tras autenticarse

#### Scenario: Estado de carga durante rehidratación
- **WHEN** la sesión todavía se está rehidratando (refresh en curso al cargar la app)
- **THEN** `ProtectedRoute` muestra un estado de carga y no decide la redirección hasta resolver si la sesión es válida

### Requirement: Guard de autorización por rol

El componente `ProtectedRoute` SHALL aceptar opcionalmente uno o más roles requeridos. Un usuario autenticado cuyo conjunto de roles no incluya ninguno de los roles requeridos SHALL ver una pantalla `403` (o ser redirigido), sin renderizar el contenido protegido. La verificación es fail-closed: sin rol coincidente, no hay acceso.

#### Scenario: Usuario con rol requerido accede
- **WHEN** una ruta exige el rol COORDINADOR y el usuario autenticado tiene COORDINADOR entre sus roles
- **THEN** el sistema renderiza el contenido de la ruta

#### Scenario: Usuario sin rol requerido es bloqueado
- **WHEN** una ruta exige el rol FINANZAS y el usuario autenticado no lo tiene
- **THEN** el sistema muestra la pantalla `403` y no renderiza el contenido protegido

#### Scenario: Múltiples roles aceptados
- **WHEN** una ruta acepta los roles COORDINADOR o ADMIN y el usuario tiene ADMIN
- **THEN** el sistema renderiza el contenido de la ruta

### Requirement: Shell y layout principal

El frontend SHALL proveer un layout raíz autenticado compuesto por una barra de navegación lateral (sidebar), una barra superior (topbar) con la identidad del usuario y la acción de logout, y un área de contenido donde se montan las rutas de las features. El ruteo SHALL usar React Router con lazy loading de las features para no cargar todo el bundle por adelantado.

#### Scenario: Layout envuelve las rutas privadas
- **WHEN** un usuario autenticado navega entre rutas privadas
- **THEN** el sidebar y la topbar permanecen visibles y solo el área de contenido cambia según la ruta

#### Scenario: Carga diferida de features
- **WHEN** el usuario accede por primera vez a una ruta de una feature
- **THEN** el bundle de esa feature se carga de forma diferida (lazy) y muestra un fallback de carga mientras llega

#### Scenario: La topbar expone la identidad y el logout
- **WHEN** el usuario autenticado ve el layout
- **THEN** la topbar muestra su identidad y ofrece la acción de cerrar sesión

### Requirement: Navegación por rol

El sidebar SHALL construir su lista de items dinámicamente a partir de los roles de la sesión, mostrando únicamente los destinos a los que el rol del usuario tiene acceso y ocultando el resto. Un usuario con múltiples roles SHALL ver la unión de los items de todos sus roles.

#### Scenario: El menú se adapta al rol
- **WHEN** un usuario con rol FINANZAS visualiza el sidebar
- **THEN** ve los items correspondientes a FINANZAS y no ve items exclusivos de otros roles (por ejemplo, gestión de estructura académica del ADMIN)

#### Scenario: Usuario con múltiples roles ve la unión
- **WHEN** un usuario tiene los roles PROFESOR y COORDINADOR
- **THEN** el sidebar muestra la unión de los items de ambos roles, sin duplicados

#### Scenario: Sin items para un rol sin destinos
- **WHEN** un rol no tiene destinos de navegación habilitados en el shell
- **THEN** el sidebar no muestra items para ese rol y el resto del layout sigue operativo

### Requirement: Pantalla de ruta inexistente

El frontend SHALL mostrar una pantalla de "no encontrado" (404) cuando el usuario navegue a una ruta que no existe dentro de la aplicación.

#### Scenario: Ruta inexistente
- **WHEN** un usuario autenticado navega a una URL que no corresponde a ninguna ruta registrada
- **THEN** el sistema muestra la pantalla de "no encontrado" sin romper el layout
