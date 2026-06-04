## ADDED Requirements

### Requirement: Cómputo de alumnos atrasados (RN-06)
El sistema SHALL computar, para una materia y cohorte dadas y un conjunto de actividades seleccionadas, la lista de alumnos **atrasados**. Un alumno se considera atrasado si cumple al menos una de estas condiciones: (a) tiene al menos una actividad seleccionada sin calificación registrada (faltante), o (b) tiene al menos una calificación con `aprobado = False` (nota por debajo del umbral efectivo o valor textual no aprobatorio). El cómputo SHALL evaluarse sobre las calificaciones del importador (RN-04) y scopearse por `tenant_id` de la sesión. El umbral ya está reflejado en el campo `aprobado` persistido por C-10.

#### Scenario: Alumno con actividad faltante es atrasado
- **WHEN** se computan los atrasados para las actividades seleccionadas [A, B] y un alumno tiene calificación sólo en A
- **THEN** el alumno aparece en la lista de atrasados con la actividad B marcada como faltante

#### Scenario: Alumno con nota por debajo del umbral es atrasado
- **WHEN** un alumno tiene calificación en todas las actividades seleccionadas pero al menos una tiene `aprobado = False`
- **THEN** el alumno aparece en la lista de atrasados con esa actividad marcada como no aprobada

#### Scenario: Alumno al día no aparece en la lista
- **WHEN** un alumno tiene calificación en todas las actividades seleccionadas y todas con `aprobado = True`
- **THEN** el alumno NO aparece en la lista de atrasados

#### Scenario: El cómputo es scope-isolated por importador (RN-04)
- **WHEN** PROFESOR A y PROFESOR B importaron calificaciones para la misma materia M
- **THEN** el cómputo de atrasados solicitado por A considera únicamente las calificaciones importadas por A
- **AND** las calificaciones importadas por B no afectan el resultado de A

#### Scenario: Aislamiento por tenant en el cómputo
- **WHEN** el tenant T1 solicita el cómputo de atrasados para una materia
- **THEN** ninguna calificación ni entrada de padrón del tenant T2 se incluye en el resultado
- **AND** toda query filtra por `tenant_id` de la sesión

#### Scenario: Sin actividades seleccionadas devuelve estado informativo
- **WHEN** se solicita el cómputo de atrasados con la lista de actividades seleccionadas vacía
- **THEN** el sistema devuelve una lista de atrasados vacía y una marca de "sin datos para analizar"

---

### Requirement: Ranking de actividades aprobadas (RN-09)
El sistema SHALL producir un ranking de alumnos ordenado de forma descendente por la cantidad de actividades aprobadas (`aprobado = True`) entre las actividades seleccionadas. El ranking SHALL incluir **únicamente** alumnos con al menos una actividad aprobada; los alumnos sin ninguna aprobada NO SHALL aparecer. El ranking SHALL scopearse por `tenant_id` de la sesión y por importador (RN-04).

#### Scenario: Alumno sin aprobadas se excluye del ranking
- **WHEN** se computa el ranking y un alumno no tiene ninguna actividad con `aprobado = True`
- **THEN** ese alumno NO aparece en el ranking (RN-09)

#### Scenario: Alumnos se ordenan por cantidad de aprobadas descendente
- **WHEN** el alumno X tiene 3 actividades aprobadas y el alumno Y tiene 1
- **THEN** X aparece antes que Y en el ranking
- **AND** cada fila reporta el alumno y su conteo de actividades aprobadas

#### Scenario: Sólo cuenta actividades seleccionadas
- **WHEN** un alumno tiene una actividad aprobada que NO está entre las seleccionadas
- **THEN** esa actividad no se cuenta en su total del ranking

---

### Requirement: Reportes rápidos por materia (F2.4)
El sistema SHALL exponer un reporte consolidado por materia y cohorte con métricas derivadas de las calificaciones importadas: total de actividades seleccionadas, cantidad de alumnos, cantidad de alumnos atrasados, cantidad de calificaciones aprobadas y tasa de aprobación. Cuando no haya calificaciones o no se hayan seleccionado actividades, el reporte SHALL devolver un estado informativo en lugar de un error.

#### Scenario: Reporte con datos devuelve métricas consolidadas
- **WHEN** existen calificaciones para la materia y se seleccionaron actividades
- **THEN** el reporte devuelve total de actividades, total de alumnos, atrasados, aprobadas y tasa de aprobación

#### Scenario: Reporte sin datos devuelve estado informativo
- **WHEN** no existen calificaciones para la materia, o no se seleccionaron actividades
- **THEN** el reporte devuelve un estado "sin datos" con métricas en cero, sin error HTTP

#### Scenario: Métricas scopeadas por tenant e importador
- **WHEN** se solicita el reporte de una materia
- **THEN** las métricas consideran sólo calificaciones del tenant de la sesión e importadas por el usuario actual (RN-04)

---

### Requirement: Notas finales agrupadas (F2.5)
El sistema SHALL calcular una nota final por alumno agrupando las actividades seleccionadas de una materia. La nota final SHALL derivarse de las calificaciones del alumno sobre esas actividades de forma determinista (sin efectos secundarios) y SHALL incluir, por alumno, su identificador de padrón y el detalle de aprobación. El resultado SHALL scopearse por `tenant_id` de la sesión y por importador (RN-04).

#### Scenario: Nota final agrupa las actividades seleccionadas
- **WHEN** un alumno tiene calificaciones numéricas en las actividades seleccionadas
- **THEN** el sistema devuelve una nota final por alumno calculada a partir de esas calificaciones

#### Scenario: Alumno sin calificaciones no rompe el cálculo
- **WHEN** un alumno del padrón no tiene calificaciones en las actividades seleccionadas
- **THEN** el sistema devuelve ese alumno con nota final ausente/cero, sin error

#### Scenario: El cálculo de nota final es determinista
- **WHEN** se calcula la nota final dos veces para el mismo conjunto de calificaciones
- **THEN** el resultado es idéntico en ambas ejecuciones

---

### Requirement: Acceso no autorizado al análisis devuelve 403
El sistema SHALL rechazar todos los endpoints de análisis académico para usuarios sin el permiso `atrasados:ver`, siguiendo la política RBAC fail-closed. La identidad, los roles y el tenant SHALL resolverse exclusivamente desde la sesión JWT, nunca desde parámetros de la petición.

#### Scenario: Usuario sin atrasados:ver no puede acceder al análisis
- **WHEN** un usuario sin el permiso `atrasados:ver` llama a cualquier endpoint de `/api/analisis`
- **THEN** el sistema responde HTTP 403

#### Scenario: Petición no autenticada es rechazada
- **WHEN** una petición a cualquier endpoint de análisis llega sin un JWT válido
- **THEN** el sistema responde HTTP 401

#### Scenario: El scope no puede alterarse desde la petición
- **WHEN** un usuario envía un `tenant_id` o `usuario_id` en el body o query distinto al de su sesión
- **THEN** el sistema ignora esos valores y resuelve identidad y tenant desde el JWT
