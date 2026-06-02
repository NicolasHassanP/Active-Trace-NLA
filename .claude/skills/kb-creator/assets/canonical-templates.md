# Canonical Templates — Estructura interna de cada archivo

Esta es la estructura **mínima esperada** de cada uno de los 10 archivos canónicos. Adaptala según el dominio, pero respetá las secciones marcadas como obligatorias.

---

## 01_vision_y_objetivos.md

```markdown
# Visión y Objetivos

## Propósito del sistema
[Una frase + un párrafo de contexto.]

## Objetivos por actor
[Tabla: Actor → Objetivo principal → Objetivos secundarios]

## Alcance v{X.Y}
[Bullet list de qué SÍ hace el sistema en esta versión.]

## Fuera de alcance
[Bullet list de qué NO hace, explícitamente.]

## Métricas de éxito
[Cómo se mide que el sistema cumple su propósito — opcional pero recomendado.]
```

---

## 02_descripcion_general.md

```markdown
# Descripción General

## Stack tecnológico
[Tabla: Capa → Tecnologías → Versión mínima]

## Arquitectura general
[Diagrama ASCII o descripción + justificación de decisiones de alto nivel.]

## Integraciones externas
[Tabla: Servicio → Propósito → Tipo (REST/webhook/SDK)]

## API REST (si aplica)
[Resumen de endpoints principales agrupados por recurso.]
```

---

## 03_actores_y_roles.md

```markdown
# Actores y Roles

## Actores del sistema
[Tabla: Actor → Descripción → Cómo interactúa]

## RBAC — Matriz de permisos
[Tabla: Rol → Recurso → Permisos (CRUD)]

## Rutas públicas
[Lista de rutas accesibles sin autenticación.]
```

---

## 04_modelo_de_datos.md

```markdown
# Modelo de Datos

## Dominios
[Lista de dominios del sistema con breve descripción.]

## ERD (Entity Relationship Diagram)
[Diagrama ASCII o descripción textual de relaciones.]

## Entidades
### {Nombre entidad}
- Atributos (con tipo)
- Relaciones (con cardinalidad)
- Constraints
- Índices relevantes

## Seed data inicial
[Datos mínimos requeridos al arrancar el sistema.]
```

---

## 05_reglas_de_negocio.md

```markdown
# Reglas de Negocio

Cada regla tiene un código único `RN-{DOMINIO}-{NN}` para trazabilidad.

## Dominio: Autenticación (RN-AU)
- **RN-AU-01**: [Regla] — [Justificación si no es obvia]

## Dominio: {Otro}
...

## Dominio: Excepciones globales
[Reglas que cruzan múltiples dominios.]
```

---

## 06_funcionalidades.md

```markdown
# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN).

## Épica 1: {Nombre}
### US-001 — {Título}
**Como** [actor]
**Quiero** [acción]
**Para** [beneficio]

**Criterios de aceptación**:
- [ ] CA-1
- [ ] CA-2

**Reglas relacionadas**: RN-XX-NN, RN-YY-MM
```

---

## 07_flujos_principales.md

```markdown
# Flujos Principales

Cada flujo se documenta extremo a extremo, mostrando interacciones entre componentes.

## Flujo 1: {Nombre}
**Disparador**: [evento]
**Actor**: [quién inicia]

**Pasos**:
1. [Componente] hace X
2. [Componente] hace Y
3. ...

**Diagrama de secuencia** (opcional, ASCII):
```
Actor → Frontend → API → DB
                         ← respuesta
```

**Casos de error**:
- [Caso] → [Manejo]
```

---

## 08_arquitectura_propuesta.md

```markdown
# Arquitectura Propuesta

## Patrones aplicados
[Tabla: Patrón → Dónde se usa → Por qué]

## Estructura de directorios
```
proyecto/
├── backend/
│   └── app/
│       ├── domain/
│       ├── infrastructure/
│       └── application/
└── frontend/
    └── src/
        ├── features/
        ├── shared/
        └── pages/
```

## Seguridad
- Autenticación: [esquema]
- Autorización: [esquema]
- Validación de input: [enfoque]
- Secrets management: [enfoque]

## Variables de entorno
[Tabla: Variable → Descripción → Ejemplo → Sensible (Y/N)]
```

---

## 09_decisiones_y_supuestos.md

```markdown
# Decisiones y Supuestos

## Decisiones documentadas
### DD-01 — {Título}
**Decisión**: [qué se decidió]
**Contexto**: [por qué hubo que decidir]
**Alternativas consideradas**: [opciones evaluadas]
**Justificación**: [por qué se eligió esta]
**Trade-offs aceptados**: [qué se resigna]

## Supuestos inferidos
### SU-01 — {Título}
**Supuesto**: [qué se asume]
**Origen**: [de qué documento/conversación se infirió]
**Riesgo si es falso**: [impacto]
**Cómo validar**: [acción concreta]
```

---

## 10_preguntas_abiertas.md

```markdown
# Preguntas Abiertas

## Inconsistencias detectadas
### IN-01 — {Título}
**Documento A dice**: [...]
**Documento B dice**: [...]
**Impacto**: [qué se rompe si no se resuelve]
**Resolución propuesta**: [opción recomendada]

## Preguntas abiertas (priorizadas)
| Prioridad | Pregunta | Bloquea | Decisor |
|-----------|----------|---------|---------|
| Alta | ... | Sprint 1 | Product Owner |
| Media | ... | Sprint 3 | Equipo técnico |
| Baja | ... | Lanzamiento | Tech Lead |
```

---

## README.md (índice)

```markdown
# {Proyecto} — Base de Conocimiento

Base de conocimiento generada a partir de los documentos del proyecto.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | ... |
| [02_descripcion_general.md](02_descripcion_general.md) | ... |
| ... |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

[2-3 frases con lo más importante del sistema.]
```
