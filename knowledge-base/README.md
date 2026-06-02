# Knowledge Base — activia-trace

> **Propósito**: este directorio es la **base de conocimiento de producto** de activia-trace. Describe QUÉ hace el sistema en términos de dominio: actores, reglas de negocio, flujos, datos y funcionalidades. Es completamente agnóstica de tecnología y reutilizable por cualquier equipo para construir el sistema desde cero.
>
> El detalle técnico (stack, arquitectura, patrones de implementación) vive en [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md). Los requerimientos de producto están en [`../docs/PRD.md`](../docs/PRD.md).

---

## ¿Qué es activia-trace?

**activia-trace** es una plataforma de gestión académica y trazabilidad de actividades estudiantiles. Opera como capa de gestión sobre un LMS (sistema de gestión del aprendizaje), extendiendo sus capacidades con seguimiento de rendimiento, comunicación dirigida, gestión de equipos docentes y liquidaciones de honorarios.

El sistema es **multi-tenant**: cada institución educativa opera en un entorno completamente aislado. Los actores y sus permisos se rigen por un modelo **RBAC con permisos finos**. Toda acción significativa queda registrada en la **auditoría**.

---

## Contenido de la KB

| # | Archivo | Contenido |
|---|---------|-----------|
| 01 | [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito del sistema, objetivos por actor, alcance y fuera de alcance |
| 02 | [02_descripcion_general.md](02_descripcion_general.md) | Descripción funcional del sistema, módulos principales e integraciones de negocio |
| 03 | [03_actores_y_roles.md](03_actores_y_roles.md) | Actores del dominio, modelo RBAC, matriz de capacidades y reglas de autorización |
| 04 | [04_modelo_de_datos.md](04_modelo_de_datos.md) | Entidades del dominio, relaciones y modelo de datos conceptual |
| 05 | [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas de negocio codificadas (RN-XX) organizadas por dominio |
| 06 | [06_funcionalidades.md](06_funcionalidades.md) | Funcionalidades del sistema organizadas por épica |
| 07 | [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo: importación de calificaciones, mensajería, autenticación, etc. |
| 08 | [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Decisiones de arquitectura de producto y patrones de diseño del sistema |
| 09 | [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones de diseño adoptadas y supuestos base del sistema |
| 10 | [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Aspectos del dominio pendientes de validación con el responsable de producto |
| 11 | [11_historias_de_usuario.md](11_historias_de_usuario.md) | Historias de usuario (formato Connextra + criterios de aceptación), cruzadas con funcionalidades y reglas |

---

## Supuestos base (ya decididos)

Estos supuestos aplican a toda la KB. No requieren validación adicional:

- **Multi-tenant**: cada institución es un tenant aislado; sus datos nunca se cruzan con los de otro tenant.
- **RBAC con permisos finos**: la autorización se basa en permisos atómicos (`modulo:accion`), no en flags binarios. Ver [03_actores_y_roles.md](03_actores_y_roles.md).
- **Identidad desde la sesión**: la identidad, los roles y el tenant de un usuario se derivan exclusivamente de su sesión autenticada. Ningún dato de la petición puede alterar quién es el usuario ni qué permisos tiene.
- **Auditoría completa**: toda acción significativa sobre el sistema queda registrada con actor, timestamp y contexto.

---

## Roles del dominio

ALUMNO · TUTOR · PROFESOR · COORDINADOR · NEXO · ADMIN · FINANZAS

El detalle de responsabilidades y permisos de cada rol está en [03_actores_y_roles.md](03_actores_y_roles.md).

---

## Cómo usar esta KB

1. Empezá por [01_vision_y_objetivos.md](01_vision_y_objetivos.md) para entender el propósito del sistema.
2. Leé [03_actores_y_roles.md](03_actores_y_roles.md) para internalizar el modelo de permisos antes de cualquier implementación.
3. Consultá [05_reglas_de_negocio.md](05_reglas_de_negocio.md) y [06_funcionalidades.md](06_funcionalidades.md) para entender qué hace el sistema en detalle.
4. Usá [10_preguntas_abiertas.md](10_preguntas_abiertas.md) como backlog de validación con el dueño de producto.
5. Para el detalle técnico de implementación, referite a [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md).
