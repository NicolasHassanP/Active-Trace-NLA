## ADDED Requirements

### Requirement: Límite de intentos de autenticación por IP y email

El sistema SHALL limitar los intentos en `POST /api/auth/login` (y `POST /api/auth/forgot`) a **5 intentos por ventana de 60 segundos** por la clave compuesta `(IP del cliente, email normalizado)`. Al exceder el límite, el sistema SHALL responder `429 Too Many Requests`.

#### Scenario: Bajo el límite
- **WHEN** se realizan hasta 5 intentos de login en 60s para la misma (IP, email)
- **THEN** el sistema procesa cada intento normalmente

#### Scenario: Excede el límite
- **WHEN** se realiza un sexto intento dentro de la misma ventana de 60s para la misma (IP, email)
- **THEN** el sistema responde `429` sin procesar las credenciales

#### Scenario: La ventana se reinicia
- **WHEN** transcurren más de 60s desde el primer intento
- **THEN** el contador se reinicia y se permiten nuevos intentos

### Requirement: Fail-closed del rate limiter

Si el backend del limitador de tasa no está disponible, el sistema SHALL denegar la operación (fail-closed) en lugar de permitirla sin límite.

#### Scenario: Backend del limitador caído
- **WHEN** el backend del rate limiter falla al evaluar un intento de login
- **THEN** el sistema deniega la request en vez de permitir intentos ilimitados
