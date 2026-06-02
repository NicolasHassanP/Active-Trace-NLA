# 03 — Actores y Roles

> **Propósito**: definir QUIÉNES usan el sistema y QUÉ puede hacer cada uno. Escrito en lenguaje de dominio y agnóstico de tecnología: describe el modelo de permisos a construir, no una implementación concreta. El detalle técnico de cómo se implementa la seguridad vive en [`docs/ARQUITECTURA.md` §5](../docs/ARQUITECTURA.md).

---

## 1. Concepto: identidad, rol y tenant

El sistema es **multi-institución (multi-tenant)**. Cada institución es un **tenant** aislado: sus datos jamás se cruzan con los de otra. Todo usuario pertenece a exactamente un tenant.

Dentro de un tenant, cada usuario tiene:

- **Una identidad** — quién es la persona (única e inmutable dentro del tenant).
- **Uno o más roles** — qué función cumple (un usuario puede ser, por ejemplo, PROFESOR y COORDINADOR a la vez).
- **Un conjunto de permisos efectivos** — qué acciones concretas puede ejecutar, derivados de sus roles.

> 🔑 **Regla de oro (no negociable)**: la identidad, los roles y el tenant de un usuario se derivan **exclusivamente de su sesión autenticada**. Ningún dato de la petición (parámetro de URL, campo de formulario, encabezado) puede cambiar quién es el usuario ni qué permisos tiene. Esta regla es la base de todo el modelo de seguridad.

---

## 2. Roles del dominio

El sistema define los siguientes roles. Cada uno representa una **función**, no un nivel de privilegio acumulativo: un ADMIN no es "un PROFESOR con más permisos", son funciones distintas con permisos distintos.

| Rol | Quién es | Responsabilidad principal |
|-----|----------|---------------------------|
| **ALUMNO** | Estudiante que cursa materias | Consultar su propio estado académico, reservar instancias de evaluación, confirmar avisos. |
| **TUTOR** | Auxiliar / ayudante de cátedra | Acompañar el seguimiento de alumnos, cubrir guardias, asistir al profesor. |
| **PROFESOR** | Docente a cargo de una o más comisiones | Gestionar sus comisiones: calificaciones, detección de atrasados, comunicación con alumnos, encuentros. |
| **COORDINADOR** | Responsable de un conjunto de materias o de una cohorte | Armar equipos docentes, supervisar rendimiento, publicar avisos, coordinar tareas. |
| **NEXO** | Rol de articulación / enlace transversal | Cumple funciones de puente entre la institución y grupos de docentes o alumnos (no atado a una materia específica). |
| **ADMIN** | Administrador del sistema dentro del tenant | Gestionar la estructura académica (carreras, cohortes, materias), usuarios y configuración del tenant. |
| **FINANZAS** | Responsable de liquidaciones y honorarios | Operar la grilla salarial, calcular y cerrar liquidaciones, gestionar facturas. |

> ℹ️ **Extensibilidad**: el conjunto de roles debe ser un catálogo administrable por tenant, no una lista fija en código. Una institución podría necesitar un rol que otra no use.

---

## 3. Modelo de autorización (RBAC con permisos finos)

La autorización se basa en **permisos finos por capacidad**, agrupados en roles. **No** existe un "flag de superusuario" binario: cada acción protegida exige un permiso explícito.

### 3.1 Permisos

Un **permiso** es una capacidad atómica sobre un módulo, expresada como `modulo:accion`. Ejemplos:

- `calificaciones:importar`
- `atrasados:ver`
- `comunicacion:enviar`
- `comunicacion:aprobar`
- `equipos:asignar`
- `liquidaciones:cerrar`
- `auditoria:ver`
- `impersonacion:usar`

### 3.2 Roles como conjuntos de permisos

Cada rol agrupa un conjunto de permisos. Los permisos efectivos de un usuario son la **unión** de los permisos de todos sus roles, **acotados por su tenant** y por la **vigencia** de sus asignaciones (ver §5).

### 3.3 Matriz de capacidades por rol

> La matriz se expresa por **capacidad de negocio**, no por pantalla ni ruta, para que sea implementable en cualquier arquitectura. `✅` = el rol tiene la capacidad; `—` = no la tiene; `(propio)` = solo sobre sus propios datos, no los de otros usuarios.

| Capacidad / Módulo | ALUMNO | TUTOR | PROFESOR | COORDINADOR | ADMIN | FINANZAS |
|--------------------|:------:|:-----:|:--------:|:-----------:|:-----:|:--------:|
| Ver estado académico propio | ✅ | — | — | — | — | — |
| Reservar instancia de evaluación | ✅ | — | — | — | — | — |
| Confirmar avisos (acknowledgment) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Importar calificaciones | — | — | ✅ (propio) | ✅ | ✅ | — |
| Ver alumnos atrasados | — | ✅ | ✅ (propio) | ✅ | ✅ | — |
| Detectar entregas sin corregir | — | ✅ | ✅ (propio) | ✅ | ✅ | — |
| Enviar comunicaciones a alumnos | — | — | ✅ (propio) | ✅ | ✅ | — |
| Aprobar comunicaciones masivas | — | — | — | ✅ | ✅ | — |
| Gestionar encuentros | — | ✅ | ✅ (propio) | ✅ | ✅ | — |
| Registrar guardias | — | ✅ (propio) | ✅ (propio) | ✅ | ✅ | — |
| Gestionar tareas internas | — | — | ✅ (propio) | ✅ | ✅ | — |
| Publicar avisos | — | — | — | ✅ | ✅ | — |
| Gestionar equipos docentes (asignaciones) | — | — | — | ✅ | ✅ | — |
| Gestionar estructura académica (carreras, cohortes, materias) | — | — | — | — | ✅ | — |
| Gestionar usuarios del tenant | — | — | — | — | ✅ | — |
| Ver auditoría | — | — | — | ✅ (propio) | ✅ | ✅ |
| Operar grilla salarial | — | — | — | — | — | ✅ |
| Calcular / cerrar liquidaciones | — | — | — | — | — | ✅ |
| Gestionar facturas | — | — | — | — | — | ✅ |
| Configurar el tenant | — | — | — | — | ✅ | — |

> ⚠️ Esta matriz es el **punto de partida** del diseño de permisos. El equipo de implementación debe modelarla como datos (catálogo rol × permiso administrable), no hardcodearla.

---

## 4. Impersonación (suplantación legítima)

El sistema **puede** permitir que un usuario autorizado (típicamente soporte o ADMIN) opere temporalmente "en nombre de" otro usuario, para diagnóstico o asistencia. Esta capacidad es **opcional, peligrosa y debe estar fuertemente controlada**:

- Requiere el permiso explícito `impersonacion:usar`.
- Genera una sesión claramente distinguible de una sesión normal.
- **Toda acción realizada bajo impersonación queda atribuida al actor real** (quién impersona), no a la persona impersonada — para no romper la trazabilidad.
- Cada inicio y fin de impersonación se **registra en la auditoría**: quién, a quién, desde cuándo, hasta cuándo.

> La impersonación **nunca** puede activarse alterando un dato de la petición. Es siempre una acción explícita, permisada y auditada.

---

## 5. Vigencia temporal de las asignaciones

Los permisos de un usuario sobre un contexto académico (una materia, una comisión) están condicionados por la **vigencia** de su asignación:

- Cada asignación rol↔contexto tiene una fecha **desde** y una fecha **hasta** (esta última puede ser abierta).
- Una asignación está **vigente** si la fecha actual cae dentro de su rango.
- Un usuario **solo** ejerce los permisos de una asignación mientras esté vigente. Una asignación vencida no otorga acceso, pero **se conserva en el histórico** (no se borra) para auditoría y para clonado entre períodos.

Esto permite la rotación natural de docentes entre cuatrimestres sin perder el registro histórico.

---

## 6. Acceso anónimo (no autenticado)

Las únicas operaciones accesibles **sin sesión iniciada** son las del flujo de autenticación:

- Pantalla de inicio de sesión (login).
- Solicitud y confirmación de recuperación de contraseña.

**Cualquier otra operación exige una sesión autenticada válida.** No existe ninguna ruta, parámetro ni atajo que otorgue acceso a datos o acciones sin pasar por la autenticación. El flujo de login está en [07 — Flujos Principales](07_flujos_principales.md) y su implementación en [`docs/ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md).

---

## 7. Resumen para el equipo de implementación

1. **Multi-tenant**: todo dato y todo permiso vive dentro de un tenant; nunca se cruzan.
2. **Identidad desde la sesión, jamás desde la petición** — regla de seguridad #1.
3. **RBAC con permisos finos** (`modulo:accion`), no flags binarios; catálogo rol × permiso administrable como datos.
4. **Roles del dominio**: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS.
5. **Vigencia temporal** acota qué asignaciones están activas; el histórico se conserva.
6. **Impersonación** solo permisada, distinguible y auditada.
