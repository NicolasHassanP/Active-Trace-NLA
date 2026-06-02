# 05 — Reglas de Negocio

> **Propósito**: documentar las reglas que el sistema debe hacer cumplir, independientemente de cómo se implemente. Cada regla tiene un código estable `RN-XX` para ser referenciada desde otros archivos de la KB. El lenguaje es de dominio: describe QUÉ debe ocurrir, no CÓMO lo resuelve una tecnología concreta. El detalle de implementación vive en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).

---

## Dominio: Importación de Calificaciones

### RN-01 — Detección de columnas de nota numérica
En el archivo de calificaciones exportado desde el LMS, las columnas que el sistema interpreta como **nota numérica redondeada** son aquellas cuyo encabezado termina en `(Real)`. Cualquier otra columna no se procesa como nota numérica.

### RN-02 — Mapeo de escala textual a aprobado
Los valores textuales **"Satisfactorio"** y **"Supera lo esperado"** se almacenan como nota en escala textual y **cuentan como aprobado** para todos los efectos de seguimiento. Valores como "No satisfactorio" o "No alcanzado" no cuentan como aprobado. La lista completa de valores válidos de la escala es un parámetro de configuración del sistema.

### RN-03 — Umbral de nota por defecto
El umbral mínimo para considerar que un alumno no está en situación de riesgo por nota baja es del **60 % de la nota máxima posible**, configurado por defecto. Este umbral es configurable por docente por materia; si no se ajusta, rige el valor predeterminado.

### RN-04 — Borrado de datos es scope-isolated
La operación de vaciado de calificaciones de una materia elimina **únicamente los datos del usuario que la ejecuta en esa materia**. No afecta los datos cargados por otros docentes en la misma materia. El scope de los datos importados es siempre `(usuario_id × materia_id)`.

### RN-05 — Importación de padrón es upsert destructivo
Al importar un nuevo padrón de participantes para una materia, la carga reemplaza completamente el padrón anterior de esa materia. No se conserva historial de versiones del padrón: si un alumno estaba en el padrón anterior y no figura en el nuevo, deja de estar registrado en el sistema para esa materia.

---

## Dominio: Detección de Atrasados y Pendientes

### RN-06 — Definición de "alumno atrasado"
Un alumno se considera **atrasado** si cumple al menos una de estas condiciones:
- Tiene actividades sin entregar (faltantes).
- Tiene nota registrada inferior al umbral configurado (ver RN-03).

### RN-07 — Detección de entregas sin calificar
El sistema cruza el reporte de finalización del LMS con las calificaciones importadas para identificar entregas que están **finalizadas por el alumno pero que aún no tienen calificación**. Esas entregas son las que se reportan como "posibles trabajos sin corregir".

### RN-08 — Detección de trabajos sin corregir aplica solo a actividades de escala textual
La tabla de posibles entregas sin corregir agrupa **únicamente actividades de escala textual** (cualitativa). Las actividades de escala numérica no se incluyen porque en esa escala la ausencia de nota equivale a no entregado, no a pendiente de corrección.

---

## Dominio: Ranking y Reportes

### RN-09 — Ranking de actividades aprobadas excluye alumnos sin aprobadas
El ranking "Realización de actividades aprobadas" lista **solo alumnos con al menos una actividad aprobada**. Los alumnos sin ninguna aprobada no aparecen en este ranking.

---

## Dominio: Equipos Docentes

### RN-10 — Vigencia determina el estado de una asignación docente
Una asignación profesor ↔ materia se considera **vigente** si la fecha actual cae dentro del rango `desde`–`hasta` de esa asignación. Una asignación fuera de rango está inactiva pero se conserva en el histórico (ver [03 — Actores y Roles §5](03_actores_y_roles.md)).

### RN-11 — Jerarquía de reporte entre docentes
Una asignación puede declarar uno o más usuarios que **responden** por ese docente en esa comisión. Esto modela la cadena de coordinación: un coordinador puede indicar a qué profesores supervisa dentro de cada materia.

### RN-12 — Clonación de equipo entre cohortes
Existe la operación de **clonado de equipo docente**: duplica todas las asignaciones de un equipo (materia × carrera × cohorte origen) hacia un destino (materia × carrera × cohorte destino). Caso de uso principal: al iniciar un nuevo período lectivo, se clona el equipo de la cohorte anterior para no reasignar manualmente a todos los docentes.

---

## Dominio: Encuentros

### RN-13 — Dos modos de creación de slot de encuentro
Al crear un encuentro, el sistema soporta dos modos excluyentes:
1. **Recurrente**: se define día de semana + horario + fecha de inicio + cantidad de semanas → el sistema genera automáticamente N instancias.
2. **Único**: se define una fecha individual + horario → se genera 1 instancia.

### RN-14 — Estado de instancia de encuentro es independiente del slot
Cada instancia de encuentro tiene su propio estado (programado, realizado, cancelado, reprogramado) que puede modificarse individualmente sin afectar al slot ni a otras instancias del mismo slot.

---

## Dominio: Mensajería y Comunicaciones

### RN-15 — Ciclo de vida de un mensaje saliente
Los mensajes atraviesan el siguiente ciclo de estados:
- **Pendiente** → en cola, aún no despachado.
- **Enviando** → el sistema de despacho lo tomó.
- **Enviado (OK)** → confirmación de entrega.
- **Fallido (Fail)** → error en el despacho.
- **Cancelado** → cancelado antes del despacho.

### RN-16 — Vista previa obligatoria antes de envío
Todo mensaje debe mostrarse al remitente en una vista previa (asunto + cuerpo renderizado) antes de confirmar el envío real. No existe despacho sin previa visualización y confirmación explícita del usuario.

### RN-17 — Aprobación administrativa de envíos masivos
Los envíos de alcance masivo (a múltiples destinatarios fuera del propio contexto del docente) requieren aprobación explícita por parte de un usuario con el permiso `comunicacion:aprobar` antes de pasar a estado **Enviando**. Los envíos sin aprobación permanecen en **Pendiente** hasta que se otorgue o rechace la aprobación.

---

## Dominio: Avisos

### RN-18 — Avisos tienen ventana de vigencia
Cada aviso tiene una fecha/hora de inicio (`inicio_vigencia`) y una fecha/hora de fin (`fin_vigencia`). El aviso solo es visible para los usuarios dentro de ese rango temporal.

### RN-19 — Avisos pueden requerir acuse de recibo
Si un aviso tiene `requiere_acuse = true`, el usuario debe confirmar explícitamente que lo leyó. El sistema registra cuántos usuarios lo vieron y cuántos emitieron el acuse.

### RN-20 — Avisos son segmentables por audiencia
Cada aviso define su audiencia mediante una combinación de: alcance (global, materia, cohorte), identificador de contexto (materia o cohorte específica), rol objetivo y nivel de severidad. El sistema solo muestra a cada usuario los avisos cuya audiencia lo incluye.

---

## Dominio: Liquidaciones y Salarios

### RN-21 — Estructura de liquidación: Base + Plus
La remuneración liquidada de un docente se compone de dos partes:
- **Base**: importe fijo según el rol del docente, definido en la grilla salarial vigente.
- **Plus**: adicional variable según la categoría de materia y el rol del docente para cada comisión asignada.
- **Total** = Base + Σ(Plus aplicables).

### RN-22 — Liquidación tiene ciclo cerrado e inmutable
Las liquidaciones tienen estados: **abierta** (editable) y **cerrada** (inmutable). Al ejecutar el cierre de una liquidación, su contenido queda inmutabilizado y no puede modificarse retroactivamente.

### RN-31 — Grilla salarial con vigencia temporal abierta
Las tablas de Base y Plus tienen fecha de inicio (`desde`) y fecha de fin (`hasta`) que puede ser abierta (sin fin definido). Las reglas salariales se versionan en el tiempo: al calcular una liquidación de un mes determinado, el sistema toma los valores vigentes para ese mes.

### RN-32 — Base salarial fija por rol
Existe una **base salarial fija por rol** independiente de la materia dictada. Los roles del dominio con base definida son: COORDINADOR, NEXO, PROFESOR, TUTOR. Los valores concretos son configuración de la grilla salarial, no constantes del sistema.

### RN-33 — Plus salarial por (categoría de materia × rol)
Los plus son adicionales identificados por una **clave de categoría** (por ejemplo: una categoría que agrupa materias de programación) cruzada con el rol del docente. El valor del plus es configurable en la grilla. Si un docente tiene asignaciones en N comisiones de la misma categoría, acumula N veces el plus correspondiente.

### RN-34 — Cálculo de liquidación mensual
La liquidación mensual de un docente se calcula como:
```
Total = Base(rol vigente al mes) + Σ(Plus(categoría_materia, rol) × N_comisiones)
```
donde N_comisiones es la cantidad de comisiones activas de esa categoría en el período.

### RN-35 — Docentes que facturan se liquidan por flujo separado
Los docentes configurados como "facturantes" (modalidad de pago contra factura) **no se incluyen en la liquidación general Base+Plus**. Su pago se gestiona mediante el módulo de facturas: el docente presenta la factura con el importe y el equipo de finanzas la aprueba y marca como abonada.

### RN-36 — El rol NEXO se visibiliza por separado pero suma al total
En los reportes de liquidación, los importes correspondientes al rol NEXO se presentan en una sección diferenciada para mayor visibilidad contable, pero **se incluyen en el total general** y en el resumen consolidado por docente.

### RN-37 — Liquidación se opera por (cohorte × mes)
La unidad de liquidación es la dupla **(cohorte, mes)**. Al cerrar una liquidación se inmutabiliza ese período específico para esa cohorte. Distintas cohortes tienen liquidaciones independientes.

### RN-38 — KPIs contables distinguen universo con y sin facturantes
La vista de liquidaciones expone por separado el total del universo de docentes en relación de dependencia (liquidación tradicional) y el total del universo de facturantes, para que el equipo de finanzas pueda operar ambos flujos con claridad.

### RN-39 — Facturas tienen dos estados: pendiente y abonada
Las facturas presentadas por docentes facturantes tienen exactamente dos estados:
- **Pendiente**: cargada al sistema, sin confirmación de pago.
- **Abonada**: el equipo de finanzas confirmó el pago.

### RN-40 — Estructura de una factura
Cada factura registrada contiene: referencia al docente, período (mes/año), texto de detalle libre (descripción del servicio), archivo adjunto (documento de factura), fecha de carga, tamaño del archivo, estado (RN-39) y fecha de pago si fue abonada.

---

## Dominio: Seguridad e Identidad

### RN-41 — Impersonación legítima: permisada, distinguible y auditada
El sistema puede habilitar la funcionalidad de **impersonación**, que permite a un usuario autorizado (por ejemplo, soporte o ADMIN) operar temporalmente en nombre de otro usuario. Esta funcionalidad es **opcional y fuertemente controlada**:

- Requiere el permiso explícito `impersonacion:usar` (ver [03 — Actores y Roles §4](03_actores_y_roles.md)).
- Se activa mediante una acción explícita en la interfaz, **jamás** mediante un parámetro de URL, campo de formulario u otro dato de la petición.
- La sesión impersonada es **distinguible** de una sesión normal: el sistema lo indica visualmente y técnicamente.
- **Toda acción ejecutada durante la impersonación se registra en el log de auditoría atribuida al actor real** (quien impersona), no a la persona impersonada.
- Cada inicio y fin de impersonación genera un evento de auditoría con: actor real, usuario impersonado, fecha/hora de inicio y fecha/hora de fin.

> **Regla de seguridad absoluta**: la identidad, los roles y el tenant del usuario en curso se derivan **exclusivamente de la sesión autenticada**. Ningún dato de la petición (URL, body, header) puede modificar quién es el usuario activo. Ver [03 — Actores y Roles §1](03_actores_y_roles.md) y [`docs/ARQUITECTURA.md` §5.3](../docs/ARQUITECTURA.md).

---

## Dominio: Auditoría

### RN-23 — Toda acción significativa genera un registro de auditoría
Cada acción relevante ejecutada por un usuario queda registrada con: marca de tiempo, identificador del usuario, contexto (materia u otro), código de acción, cantidad de registros afectados, dirección IP y agente de usuario del cliente. El registro es inmutable.

### RN-24 — Los códigos de acción son un catálogo cerrado
Las acciones se identifican con códigos de tipo `MODULO_ACCION` (por ejemplo: `MOD_MIS_EQUIPOS`). El catálogo de códigos válidos es un conjunto definido y versionado; no se admiten códigos arbitrarios.

---

## Dominio: Datos del Docente

### RN-25 — La identidad del docente es un identificador interno opaco
Internamente, cada usuario se identifica mediante un identificador único generado por el sistema (no expuesto en URLs ni en lógica de negocio). Si el negocio maneja un número de legajo institucional, este se almacena como **atributo de perfil** y no tiene ningún rol como credencial de autenticación, selector de identidad ni clave en URLs. Ver [03 — Actores y Roles §1](03_actores_y_roles.md).

### RN-26 — Datos bancarios requeridos para liquidar
Para que un docente pueda recibir una liquidación, debe tener registrados en su perfil: entidad bancaria, CBU y alias CBU. La ausencia de estos datos impide que el docente sea incluido en una liquidación procesable.

### RN-27 — Modalidad de facturación diferencia el tipo de contrato docente
Cada docente tiene configurada su **modalidad de pago**: relación de dependencia (liquidación tradicional Base+Plus) o facturante (pago contra factura). Esta configuración determina en qué flujo contable es procesado (RN-35). El cálculo de la remuneración puede variar según la modalidad.

---

## Dominio: Validaciones y Comportamiento de la Interfaz

### RN-28 — Toda operación de escritura requiere token de protección contra falsificación
Cada solicitud que modifique estado del sistema debe incluir un token de verificación de origen generado por el sistema para esa sesión. Las solicitudes sin token válido deben ser rechazadas.

### RN-29 — El valor "Todas" en selectores de materia tiene semántica propia
En los filtros donde se selecciona una materia, existe siempre la opción "Todas las materias" como valor explícito. Cuando está seleccionada, la operación aplica a todas las materias accesibles para el usuario en su contexto actual.

### RN-30 — Búsqueda con asistencia de autocompletado en asignación masiva
La operación de asignación masiva de docentes provee un mecanismo de búsqueda con autocompletado asistido por el servidor para localizar usuarios por nombre, apellido u otros atributos de perfil, y agregarlos a la asignación en lote.
