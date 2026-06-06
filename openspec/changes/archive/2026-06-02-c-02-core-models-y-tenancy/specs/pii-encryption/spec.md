## ADDED Requirements

### Requirement: Cifrado AES-256 en reposo de atributos sensibles

El sistema SHALL cifrar en reposo con AES-256 todo atributo marcado como `[cifrado]` (DNI, CUIL, CBU, alias CBU, email PII). El sistema SHALL proveer utilidades de cifrado y descifrado en `core/security.py` que usen la clave `ENCRYPTION_KEY` de la configuración (32 chars). El valor almacenado en la columna SHALL estar cifrado; el texto plano NUNCA SHALL persistirse en la base de datos.

#### Scenario: Round-trip de cifrado

- **WHEN** se cifra un valor de texto plano y luego se descifra el resultado
- **THEN** se recupera exactamente el valor original

#### Scenario: El valor en reposo está cifrado

- **WHEN** se persiste un atributo `[cifrado]` y se inspecciona el valor crudo en la columna
- **THEN** el valor almacenado difiere del texto plano original (está cifrado)

### Requirement: Cifrado y descifrado transparente a nivel columna

El sistema SHALL ofrecer un tipo de columna que cifre automáticamente al escribir y descifre automáticamente al leer, de modo que las entidades de negocio declaren los atributos `[cifrado]` con ese tipo y operen con texto plano en memoria sin manejar el cifrado manualmente.

#### Scenario: Escritura y lectura transparentes

- **WHEN** una entidad con un atributo declarado como cifrado se persiste y luego se vuelve a leer
- **THEN** la aplicación escribe y lee el valor en texto plano
- **AND** el cifrado/descifrado ocurre automáticamente a nivel de columna

### Requirement: PII nunca expuesta en logs ni en texto plano

El sistema NUNCA SHALL escribir atributos `[cifrado]` en texto plano en logs, mensajes de error ni representaciones de depuración (`__repr__`).

#### Scenario: PII ausente de logs

- **WHEN** se registra o representa una entidad que contiene atributos `[cifrado]`
- **THEN** el texto plano de esos atributos no aparece en la salida de log ni en la representación
