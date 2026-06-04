## ADDED Requirements

### Requirement: Monitor general de actividades (F2.7)
El sistema SHALL exponer un monitor transversal del estado de actividades de los alumnos del tenant, destinado a roles con `atrasados:ver` de scope global (COORDINADOR, ADMIN). El monitor SHALL permitir filtrar por materia, comisión, regional, búsqueda libre por alumno y estado de actividad. El alcance de los datos SHALL acotarse al `tenant_id` de la sesión.

#### Scenario: Monitor general lista alumnos del tenant con su estado
- **WHEN** un COORDINADOR con `atrasados:ver` (scope global) consulta el monitor general
- **THEN** el sistema devuelve los alumnos del tenant con su estado de actividades (atrasado / al día / sin datos)

#### Scenario: Filtro por materia acota el resultado
- **WHEN** se aplica el filtro de materia M
- **THEN** el monitor devuelve únicamente alumnos con datos en la materia M

#### Scenario: Búsqueda libre por alumno filtra por nombre o email
- **WHEN** se aplica una búsqueda libre con un término
- **THEN** el monitor devuelve únicamente alumnos cuyo nombre o email coincide con el término

#### Scenario: Aislamiento por tenant en el monitor general
- **WHEN** el tenant T1 consulta el monitor general
- **THEN** ningún alumno del tenant T2 aparece en el resultado

---

### Requirement: Monitor de seguimiento del docente (F2.8)
El sistema SHALL exponer un monitor de seguimiento que muestra el estado de actividades **únicamente de los alumnos asignados al usuario** (TUTOR, PROFESOR con `atrasados:ver` de scope propio). El conjunto de alumnos visibles SHALL derivarse de las asignaciones del usuario en la sesión (RN-04), nunca de un parámetro de la petición. El monitor SHALL permitir filtrar por alumno, email, comisión, regional, actividad y mínimo de actividades cumplidas.

#### Scenario: Docente sólo ve alumnos de sus materias asignadas
- **WHEN** un PROFESOR con `atrasados:ver` (scope propio) consulta el monitor de seguimiento
- **THEN** el monitor devuelve únicamente alumnos de las materias en las que el profesor tiene asignación vigente

#### Scenario: El docente no ve alumnos de materias ajenas
- **WHEN** existe una materia en la que el usuario no tiene asignación
- **THEN** ningún alumno de esa materia aparece en su monitor de seguimiento

#### Scenario: Filtro por mínimo de actividades cumplidas
- **WHEN** se aplica el filtro "mínimo de actividades cumplidas = N"
- **THEN** el monitor devuelve únicamente alumnos con al menos N actividades aprobadas

#### Scenario: El scope no puede ampliarse desde la petición
- **WHEN** un PROFESOR envía un identificador de otro docente o de otra materia ajena en la petición
- **THEN** el sistema ignora ese valor y resuelve el alcance desde las asignaciones del usuario autenticado

---

### Requirement: Monitor de seguimiento con rango de fechas (F2.9)
El sistema SHALL exponer una variante del monitor de seguimiento para COORDINADOR y ADMIN (scope global) que extiende el monitor del docente con un filtro adicional de **rango de fechas** sobre el período de análisis (acotando por `importado_at` de las calificaciones). Los demás filtros del monitor de seguimiento SHALL seguir disponibles.

#### Scenario: Rango de fechas acota el período de análisis
- **WHEN** un COORDINADOR consulta el monitor con un rango de fechas [desde, hasta]
- **THEN** el monitor considera únicamente calificaciones cuyo `importado_at` cae dentro del rango

#### Scenario: Coordinación ve alumnos más allá de sus propias asignaciones
- **WHEN** un COORDINADOR con `atrasados:ver` (scope global) consulta el monitor con rango de fechas
- **THEN** el resultado abarca alumnos del tenant sin restringirse a las asignaciones del coordinador

#### Scenario: Rango de fechas inválido devuelve 422
- **WHEN** se envía un rango de fechas con `desde` posterior a `hasta`
- **THEN** el sistema responde HTTP 422 con el detalle de validación

---

### Requirement: Exportar trabajos prácticos sin corregir (F2.6, RN-07/RN-08)
El sistema SHALL permitir exportar el listado de entregas detectadas como pendientes de corrección (entregas de escala textual finalizadas en el LMS sin calificación registrada). La detección SHALL aplicar la lógica de C-10 (`detectar_sin_corregir`): sólo actividades de escala textual (RN-08); las de escala numérica se excluyen. La exportación SHALL requerir el permiso `atrasados:ver` y registrar un evento de auditoría.

#### Scenario: Exportación devuelve sólo entregas textuales sin nota
- **WHEN** un usuario con `atrasados:ver` exporta los TPs sin corregir de una materia con un reporte de finalización
- **THEN** el archivo exportado incluye únicamente entregas de actividades textuales completadas sin `nota_textual` registrada (RN-07)

#### Scenario: Actividades numéricas se excluyen de la exportación (RN-08)
- **WHEN** el reporte de finalización marca como completada una actividad de escala numérica sin nota
- **THEN** esa entrega NO se incluye en la exportación

#### Scenario: La exportación registra un evento de auditoría
- **WHEN** una exportación de TPs sin corregir se completa con éxito
- **THEN** se crea un `AuditEvent` con `actor_user_id = usuario actual`, `modulo = 'atrasados'` y la cantidad de registros exportados

#### Scenario: Usuario sin permiso no puede exportar
- **WHEN** un usuario sin `atrasados:ver` solicita la exportación de TPs sin corregir
- **THEN** el sistema responde HTTP 403
