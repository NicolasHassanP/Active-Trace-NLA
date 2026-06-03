## ADDED Requirements

### Requirement: Atribución de acciones al actor real bajo impersonación

Cuando una acción se ejecuta bajo impersonación, el sistema SHALL atribuir el evento de auditoría al actor real (quien impersona) y SHALL registrar adicionalmente el usuario impersonado. La atribución (incluido el alcance de lectura "propio") SHALL basarse siempre en el actor real, nunca en el usuario impersonado.

#### Scenario: Acción bajo impersonación atribuida al actor real

- **WHEN** un actor real con permiso `impersonacion:usar` ejecuta una acción en nombre de otro usuario
- **THEN** el evento de auditoría registra al actor real como actor y al usuario impersonado como campo adicional

#### Scenario: Acción sin impersonación no registra usuario impersonado

- **WHEN** un usuario ejecuta una acción sin impersonación
- **THEN** el evento de auditoría registra al usuario como actor real y deja vacío el campo de usuario impersonado

### Requirement: Registro de inicio y fin de impersonación

El sistema SHALL registrar un evento de auditoría al iniciar una impersonación y otro al finalizarla. Cada uno SHALL incluir el actor real, el usuario impersonado y la marca temporal correspondiente.

#### Scenario: Registro de inicio de impersonación

- **WHEN** un actor real inicia una impersonación
- **THEN** el sistema registra un evento con código `IMPERSONACION_INICIO`, el actor real, el usuario impersonado y la marca de tiempo de inicio

#### Scenario: Registro de fin de impersonación

- **WHEN** finaliza una impersonación activa
- **THEN** el sistema registra un evento con código `IMPERSONACION_FIN`, el actor real, el usuario impersonado y la marca de tiempo de fin
