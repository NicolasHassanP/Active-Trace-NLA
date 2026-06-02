# Strategic Questions — Banco para Mode B (from-scratch)

Cuando entrás en Mode B, tu trabajo NO es generar archivos automáticamente sino actuar como un **arquitecto senior + product manager** que hace que el usuario clarifique su pensamiento antes de documentar.

---

## Reglas para hacer preguntas

1. **3-5 preguntas máximo por ronda.** Más es ruido.
2. Cada pregunta debe tener **opciones (a/b/c)** y un **"por qué importa"** explícito.
3. Priorizá preguntas que **bloqueen decisiones de arquitectura**, no estética.
4. **Detectá supuestos** — si el usuario dice "obvio que va con Postgres", preguntá por qué (puede ser un sesgo).

---

## Preguntas de primera ronda (las 5 fundamentales)

### P1 — Visión y problema raíz

> ¿Cuál es el **problema concreto** que este sistema resuelve, y para **quién** específicamente?

**Por qué importa**: si no podés responder esto en una frase, todo lo demás es ruido. Detecta sistemas "solución buscando problema".

**Ejemplos de respuesta débil que tenés que rechazar**: "ayudar a la gente", "modernizar el sector", "ser una plataforma digital".

---

### P2 — Alcance del MVP

> ¿Cuál es el **alcance mínimo viable** para considerar el sistema "lanzable"?

**Opciones a proponer (ajustá al dominio)**:
- (a) Solo flujo principal end-to-end con datos simulados.
- (b) Flujo principal + integración real con servicio externo crítico.
- (c) Flujo principal + integraciones + panel admin.

**Por qué importa**: define qué entra en la primera versión y qué se posterga. Vaguedad acá = scope creep en el sprint 2.

---

### P3 — Actores principales

> ¿Quiénes usan el sistema y **qué hace cada uno**? Listá los roles con UN verbo principal cada uno.

**Por qué importa**: el modelo de RBAC y la mitad de las pantallas se derivan de acá. Si confundís roles ahora, después tenés que re-modelar.

---

### P4 — Restricciones técnicas no negociables

> ¿Hay alguna restricción técnica **dada de arriba** que no podés cambiar?

**Sub-preguntas**:
- ¿Stack obligatorio (lenguaje/framework)?
- ¿Cloud específica (AWS/GCP/Azure/on-prem)?
- ¿Compatibilidad con sistemas legacy?
- ¿Compliance (GDPR, HIPAA, PCI-DSS)?

**Por qué importa**: si la restricción es real, condiciona toda la arquitectura. Si no es real (es preferencia disfrazada de restricción), evita encerrarte.

---

### P5 — Prioridades de calidad

> Si tuvieras que elegir, ¿qué priorizás: **velocidad de entrega**, **escalabilidad**, **mantenibilidad** o **costo**?

**Por qué importa**: no se puede maximizar todo. Esta respuesta filtra patrones de arquitectura. Un sistema priorizando velocidad acepta deuda técnica que uno priorizando escalabilidad no perdona.

---

## Preguntas de segunda ronda (después de las primeras 5)

Activalas según las respuestas previas.

### Si el sistema tiene transacciones financieras o datos sensibles:
- ¿Hay requisitos de auditoría (audit trail append-only)?
- ¿Cómo se manejan los rollbacks?
- ¿Hay obligación de idempotencia en operaciones críticas?

### Si el sistema tiene múltiples actores con permisos:
- ¿RBAC simple (rol → permisos) o ABAC (atributos contextuales)?
- ¿Permisos heredables entre roles?
- ¿Permisos a nivel de recurso individual?

### Si el sistema tiene flujos largos / asincrónicos:
- ¿Webhooks de servicios externos? ¿De cuáles?
- ¿Necesidad de máquina de estados explícita?
- ¿Notificaciones a usuarios (email/push/in-app)?

### Si el sistema tiene datos estructurados complejos:
- ¿Datos jerárquicos (categorías anidadas)?
- ¿Datos versionados (historial de precios, cambios de catálogo)?
- ¿Soft delete vs hard delete por entidad?

---

## Patrones de respuesta a evitar

Si el usuario responde con frases como las siguientes, **no avances** — cuestioná y pedí concreción:

| Respuesta vaga | Tu respuesta |
|----------------|--------------|
| "todo lo que se pueda" | "no podemos documentar 'todo'. Dame 3 cosas concretas en orden de prioridad." |
| "que sea escalable" | "escalable a qué escala — 100 usuarios, 100k, 100M? cada respuesta es una arquitectura distinta." |
| "como hacen otros sistemas similares" | "decime UN sistema que admires concretamente y QUÉ específico de él querés copiar." |
| "lo que sea estándar de la industria" | "no existe 'el estándar'. Dame el contexto: tipo de empresa, equipo, presupuesto." |

---

## Cierre de cada ronda de preguntas

Al final de cada ronda, escribí:

```markdown
**Resumen de lo que entendí**:
- [Punto 1]
- [Punto 2]
- ...

**Supuestos que estoy haciendo** (corregilos si no son ciertos):
- **Suposición**: [...]
- **Suposición**: [...]

**Próximos pasos propuestos**:
1. [...]
2. [...]
```

Esto deja explícito qué interpretaste y dónde podés estar errando — fuerza al usuario a corregir antes de que escribas algo malo en la KB.
