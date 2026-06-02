# 02 — Descripción General

> **Propósito**: describir QUÉ es el sistema, en qué contexto opera, qué integraciones externas tiene y cuáles son sus propiedades de seguridad fundacionales. Escrito en lenguaje de dominio, agnóstico de tecnología y de implementación. El detalle técnico de arquitectura, stack y despliegue vive en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

---

## 1. Qué es el sistema

**Activia-Trace** es una plataforma de gestión académica y trazabilidad de actividades estudiantiles. Complementa y extiende la operatoria del LMS institucional —**Moodle**—, centraliza los datos de actividad académica y habilita flujos de seguimiento, comunicación y liquidación que Moodle por sí solo no cubre.

> A lo largo de este documento, "el LMS" se refiere a **Moodle**, que es el sistema de gestión de aprendizaje con el que Activia-Trace se integra (importación de calificaciones, padrones, reportes de finalización, Web Services).

El sistema opera en modo **multi-institución (multi-tenant)**: cada institución es un tenant aislado con sus propios datos, configuración, usuarios y catálogos. Los datos de un tenant jamás son accesibles desde otro.

---

## 2. Contexto de uso

El sistema está pensado para instituciones que:

- Usan un LMS como fuente primaria de calificaciones y registro de actividad de los alumnos.
- Tienen equipos docentes con roles diferenciados (profesores, tutores, coordinadores).
- Necesitan detectar alumnos con entregas pendientes o en riesgo académico.
- Requieren flujos de comunicación controlados hacia los alumnos (con aprobación previa al envío masivo).
- Gestionan honorarios y liquidaciones de docentes.

El sistema **no reemplaza al LMS**: lo complementa. Los datos académicos se originan en el LMS y se importan hacia Activia-Trace para habilitar los flujos de seguimiento que el LMS no provee.

---

## 3. Integraciones externas

### 3.1 LMS — Moodle (fuente de datos académicos)

La integración con Moodle es **unidireccional entrante**: Moodle es la fuente de verdad de calificaciones y actividad; Activia-Trace los consume —vía Moodle Web Services y, como respaldo, importación manual de archivos exportados— pero no escribe de vuelta a Moodle de forma automática.

Los datos que se importan desde el LMS incluyen:

- **Calificaciones**: notas numéricas y calificaciones textuales (ej.: "Satisfactorio", "Supera lo esperado") por alumno y por actividad evaluativa.
- **Reporte de finalización de actividades**: indica qué actividades completó cada alumno.
- **Padrón de participantes**: listado de alumnos por comisión.
- **Padrón de actividades**: catálogo de actividades evaluativas de cada materia.

**Reglas de interpretación al importar calificaciones**:
- Las columnas que representan notas numéricas reales se redondean al valor entero más próximo.
- Los valores textuales de aprobación reconocidos (ej.: "Satisfactorio", "Supera lo esperado") se almacenan como calificación textual y cuentan como aprobado a efectos de las reglas de negocio.

**Salida hacia el LMS**: el sistema puede generar contenido formateado (ej.: fragmentos HTML) para que el docente lo copie manualmente en el aula virtual del LMS. No existe escritura automática hacia el LMS.

### 3.2 Videollamadas y grabaciones (encuentros)

Cada instancia de encuentro puede tener asociados:
- Un enlace a la sala de videollamada.
- Un enlace al video grabado de la sesión.

El sistema almacena estos enlaces; no crea ni gestiona las salas de videollamada directamente.

### 3.3 Comunicaciones por correo electrónico

El sistema gestiona el ciclo completo de envío de comunicaciones a alumnos:

- **Composición**: el docente redacta asunto y cuerpo del mensaje.
- **Vista previa**: visualización del mensaje antes de enviarlo.
- **Aprobación**: los envíos masivos requieren aprobación por parte de un rol con permiso `comunicacion:aprobar` antes de ejecutarse (ver [03 — Actores y Roles](03_actores_y_roles.md)).
- **Queue de envío**: las comunicaciones transitan por estados — Pendiente, En proceso, Enviado OK, Fallido, Cancelado.
- **Métricas por docente**: cantidad de envíos exitosos, fallidos y lotes procesados.

### 3.4 Liquidaciones y honorarios

El sistema gestiona los datos necesarios para el cálculo y cierre de liquidaciones de honorarios docentes:

- Datos bancarios del docente (banco, CBU, alias).
- Grilla salarial: base más adicionales por comisión.
- Cálculo y cierre de liquidación por período.

No se integra directamente con sistemas bancarios; la liquidación cerrada puede exportarse para su procesamiento externo.

---

## 4. Catálogo de materias por tenant

Cada tenant mantiene **un único catálogo de materias**, administrado por el rol ADMIN. No existen catálogos paralelos ni instancias separadas por programa o cohorte: si una institución tiene programas o cohortes distintos, todos los mapean al mismo catálogo de materias con sus respectivos atributos (carrera, cohorte, malla curricular).

Esto garantiza consistencia en los reportes cruzados y en la asignación de docentes. La gestión del catálogo está cubierta en [05 — Reglas de Negocio](05_reglas_de_negocio.md) y en [04 — Modelo de Datos](04_modelo_de_datos.md).

---

## 5. Propiedades de seguridad del sistema

Estas propiedades son **requisitos no funcionales de primera clase**, no opcionales ni postergables. El cómo se implementan técnicamente vive en [`docs/ARQUITECTURA.md` §5](../docs/ARQUITECTURA.md); aquí se describen como propiedades de dominio que cualquier implementación debe garantizar.

### 5.1 Multi-tenancy y aislamiento de datos

Todo dato, usuario, configuración y catálogo pertenece a un tenant. El sistema garantiza que ninguna consulta, operación ni derivación de datos puede cruzar el límite de tenant. El tenant al que pertenece un usuario se determina exclusivamente por su sesión autenticada.

### 5.2 Identidad desde la sesión, nunca desde la petición

La identidad del usuario, sus roles y su tenant se derivan **exclusivamente de su sesión autenticada**. Ningún parámetro de URL, campo de formulario, encabezado ni cualquier otro dato de la petición puede modificar quién es el usuario ni qué permisos tiene. Esta regla es la base del modelo de seguridad y no admite excepciones.

### 5.3 RBAC con permisos finos

La autorización se basa en permisos finos por capacidad (`modulo:accion`), agrupados en roles administrables. No existe un flag binario de superusuario. Cada acción protegida exige un permiso explícito. El modelo completo de roles y permisos está en [03 — Actores y Roles](03_actores_y_roles.md).

### 5.4 Auditoría de acciones significativas

Toda acción relevante (importación de datos, envío de comunicaciones, modificación de calificaciones, cierre de liquidaciones, inicio/fin de impersonación, cambios de configuración) queda registrada en el log de auditoría con: quién la ejecutó, desde qué tenant, sobre qué recurso, cuándo, y el resultado. La auditoría es inmutable y no puede ser borrada por ningún rol de usuario.

### 5.5 Protección de formularios y operaciones de escritura

Toda operación de escritura que se origine en un formulario debe estar protegida contra falsificación de petición entre sitios (CSRF). El mecanismo técnico concreto lo define [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

### 5.6 Impersonación controlada y auditada

Si el sistema habilita la suplantación de identidad para soporte o diagnóstico, esta capacidad es siempre explícita, permisada y auditada. Ver [03 — Actores y Roles §4](03_actores_y_roles.md#4-impersonación-suplantación-legítima).

---

## 6. Acceso anónimo

Las únicas operaciones disponibles sin sesión iniciada son las del flujo de autenticación (login y recuperación de contraseña). Cualquier otra operación exige una sesión autenticada válida. Ver [07 — Flujos Principales](07_flujos_principales.md).
