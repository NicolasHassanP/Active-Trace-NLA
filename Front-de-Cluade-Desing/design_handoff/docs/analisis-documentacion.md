# activia-trace — Análisis de la documentación y plan de front

> Fuente: `uploads/activia-trace-documentacion.pdf` (120 págs). Texto completo en `docs/_pdf-fulltext.txt`.
> Este doc traduce la KB/PRD a **requerimientos de front** y marca el gap con lo ya construido.

---

## 1. Qué es el producto (en una frase)
Capa de **gestión académica y trazabilidad** sobre un LMS (Moodle). No reemplaza al LMS: lo complementa con
seguimiento de rendimiento, comunicación dirigida, equipos docentes, coloquios y liquidaciones.
**Multi-tenant** (cada institución aislada), **RBAC con permisos finos** (`modulo:accion`), **todo se audita**.

## 2. El cambio grande respecto a lo que ya hicimos
Lo que construí hasta ahora es un **único panel de COORDINADOR** (un solo menú, una sola identidad).
La documentación describe un sistema **multi-rol**: la interfaz **se adapta a los permisos de la sesión**
(FL-01 paso 5). Hay **7 roles** y cada uno ve un panel distinto. Entonces el front debe:

1. **Ser role-aware**: el sidebar y las vistas cambian según el rol activo (no un menú fijo de 17 ítems).
2. **Sumar pantallas que faltan**: login, vista de ALUMNO, flujo del PROFESOR, módulo de FINANZAS,
   mensajería interna, perfil, aprobación de comunicaciones, banner de impersonación, etc.
3. **Reflejar reglas de negocio en la UI** (preview obligatorio, padrón destructivo, vigencias, ack de avisos…).

> Buena noticia: el sistema de componentes "A · Índigo" y casi todas las vistas que ya hice (Calificaciones,
> Padrón, Atrasados, Seguimiento, Equipos, Setup, Tareas, Monitor, Encuentros, Coloquios, Avisos,
> Comunicaciones, Usuarios, Estructura, Liquidaciones, Auditoría) **son reutilizables** — corresponden a las
> épicas del PRD. Faltan vistas de otros roles y ajustes de detalle.

---

## 3. Roles del dominio (RBAC) y su panel
`ALUMNO · TUTOR · PROFESOR · COORDINADOR · NEXO · ADMIN · FINANZAS` (catálogo administrable, no fijo).
Un usuario puede tener **varios roles** (ej. PROFESOR + COORDINADOR) → habrá un **switcher de rol/contexto**.

| Rol | Foco principal | Pantallas clave |
|---|---|---|
| **ALUMNO** | Su propio estado académico | Mi estado (notas/pendientes/atraso), Reservar coloquio, Avisos (con ack) |
| **TUTOR** | Acompañamiento | Atrasados (de sus comisiones), Seguimiento, Guardias (registro propio), Encuentros, Tareas, Inbox |
| **PROFESOR** | Su(s) comisión(es) | Importar calificaciones→analizar→comunicar, Atrasados, Sin corregir, Notas finales, Encuentros, Tareas, Inbox, Mis equipos |
| **COORDINADOR** | Conjunto de materias/cohorte | Monitor general, Equipos (asignar/clonar/vigencias), Avisos, Aprobar comunicaciones, Setup cuatrimestre, Tareas (admin), Auditoría (propia) |
| **NEXO** | Enlace transversal | *Semántica abierta — ver PA-25. Probablemente seguimiento + comunicación sin atarse a materia* |
| **ADMIN** | Config del tenant | Estructura académica, Usuarios/roles/permisos, Config tenant, Auditoría completa, Impersonación |
| **FINANZAS** | Honorarios | Liquidaciones (Base+Plus), Grilla salarial, Facturas, Historial, Auditoría financiera |

**Matriz de capacidades** (resumen; `(propio)` = solo sobre sus datos):
- Importar calificaciones: PROFESOR(propio), COORDINADOR, ADMIN
- Ver atrasados: TUTOR, PROFESOR(propio), COORDINADOR, ADMIN
- Enviar comunicaciones: PROFESOR(propio), COORDINADOR, ADMIN
- **Aprobar** comunicaciones masivas: COORDINADOR, ADMIN
- Publicar avisos: COORDINADOR, ADMIN
- Gestionar equipos: COORDINADOR, ADMIN
- Estructura académica / usuarios / config tenant: **ADMIN**
- Ver auditoría: COORDINADOR(propia), ADMIN, FINANZAS
- Grilla salarial / liquidar / facturas: **FINANZAS**
- Reservar evaluación / ver estado propio: **ALUMNO**

---

## 4. Pantallas requeridas por épica (catálogo de funcionalidades)
Marcado: ✅ ya construida (base) · ⚠️ construida pero hay que ajustarla a la doc · ➕ falta crear.

**Ép.1 Ingesta LMS** — Importar calificaciones ➕ (wizard real: subir→preview de actividades→elegir cuáles→umbral),
Importar reporte de finalización ➕, Importar padrón ⚠️ (es **upsert destructivo**, avisar fuerte), Vaciar datos de materia ➕.
**Ép.2 Análisis** — Atrasados ⚠️, Ranking de aprobadas ➕, Reportes rápidos por materia ➕, Notas finales agrupadas ➕,
Exportar TPs sin corregir ➕, Monitor general (coord/admin) ⚠️, Monitor seguimiento (tutor/prof) ⚠️.
**Ép.3 Comunicación** — Preview ✅(en Comunicaciones), Envío masivo con cola+estados ⚠️ (falta panel de **cola/estados**),
**Aprobación** de envíos ➕ (cola de aprobación), Mensajería interna / inbox ➕, Tablón de avisos ⚠️ (falta **ack** + severidad + vigencia).
**Ép.4 Equipos** — ABM docentes (ADMIN) ⚠️(es Usuarios), Mis equipos (docente) ➕, Consulta asignaciones ✅(Equipos),
Asignación masiva ✅, Clonar equipo ✅, Vigencia general ✅, Exportar equipo ✅.
**Ép.5 Estructura** — Carreras ⚠️, Cohortes ⚠️, Programas (subir doc) ➕, **Fechas de evaluaciones** (tabla + calendario) ➕.
**Ép.6 Encuentros** — Crear recurrente ➕(form con día/semana/#semanas), Crear único ➕, Editar instancia ➕,
Generar HTML para LMS ➕, Vista admin de encuentros ⚠️, Registro de guardias ⚠️.
**Ép.7 Coloquios** — Panel métricas ✅, Importar alumnos a convocatoria ➕, Crear convocatoria ➕(form), Listado ✅,
Admin global (convocatorias + resultados + agenda reservas) ➕.
**Ép.8 Tareas** — Mis tareas ✅, Asignar a otro docente ➕, Admin de tareas ⚠️ (falta **comentarios/hilo** + cambio de estado).
**Ép.9 Auditoría** — Panel de interacciones (gráfico por día, estado de comms por docente, métricas por docente/materia) ➕,
Log completo ⚠️.
**Ép.10 Liquidaciones** — Vista del período Base+Plus ⚠️ (falta **3 segmentos**: general / NEXO / facturantes, y KPIs "sin/con factura"),
Cerrar liquidación ➕(estado inmutable), Historial ➕, **Grilla salarial** (Base por rol + Plus por categoría) ➕, **Facturas** (ABM, pendiente/abonada) ➕.
**Ép.11 Perfil/Sesión** — Editar perfil propio (datos bancarios, facturación) ➕, Inbox ➕, Cerrar sesión ✅(existe el link).
**Ép.12 Corrección IA** — solo un acceso de menú a módulo externo (no se diseña).

**Transversales (FL/D):** **Login + 2FA + recuperar contraseña** ➕, **Banner/sesión de impersonación** ➕,
**Exportar tabular en todas las tablas** (D12) ⚠️, selector **"Todas las materias"** con semántica propia (RN-29) ➕,
**autocomplete** en asignación masiva (RN-30) ⚠️.

---

## 5. Reglas de negocio que SÍ tocan la UI
- **RN-05 / D4 — Padrón destructivo**: importar reemplaza el padrón anterior (sin historial). La UI debe **advertirlo** antes de confirmar.
  *(Ojo: en mi mock de Padrón puse "padrón versionado"; según RN-05 NO hay versiones — corregir el copy.)*
- **RN-16 / D11 — Preview obligatorio** antes de cualquier envío (individual o masivo). Ya está en Comunicaciones.
- **RN-17 / D5 — Aprobación de masivos**: estado **Pendiente** hasta que un rol con `comunicacion:aprobar` apruebe. Falta la **cola de aprobación**.
- **RN-15 — Estados de comunicación**: Pendiente → Enviando → OK / Fallido / Cancelado. Falta **panel de estado**.
- **RN-18/19/20 — Avisos**: ventana de vigencia (inicio/fin), **acuse de recibo** (require_ack) con contador, segmentación por alcance/rol/severidad. Falta en mi Avisos.
- **RN-06 — Atrasado** = actividades faltantes **o** nota < umbral. RN-03 umbral por defecto 60% configurable por docente/materia.
- **RN-07/08 — "Sin corregir"** solo aplica a actividades de **escala textual**.
- **RN-10/D8 — Vigencia temporal** de asignaciones: badge Vigente/Vencida calculado por fecha. Ya lo reflejo en Equipos.
- **RN-12/D9 — Clonar equipo** entre cohortes (primitiva del dominio). Ya está.
- **RN-21..38 — Liquidación = Base + Σ(Plus×N_comisiones)**, por (cohorte × mes), **inmutable al cerrar**;
  3 universos (dependencia / NEXO aparte pero suma / facturantes excluidos); KPIs "Total sin factura" y "Total con factura".
- **RN-26 — Sin CBU/alias/banco no se puede liquidar** (validación visible en perfil/usuarios).
- **RN-23/D6 — Auditoría inmutable**: nadie edita ni borra. Mi vista ya dice "solo lectura".
- **RN-29 — "Todas las materias"** es un valor explícito en selectores.
- **Impersonación (RN-41)**: sesión distinguible visualmente (banner), toda acción atribuida al actor real.

---

## 6. Entidades clave para poblar los mocks (modelo de datos)
Carrera, Cohorte (MAR-2026/AGO-2025), Materia (código corto `PROG_I` + nombre), Usuario (con email/dni/cuil/cbu
`[cifrado]`, regional, legajo, **facturador** bool, estado), **Asignación** (usuario×rol×materia×carrera×cohorte×comisiones,
desde/hasta, responsable_id, estado_vigencia derivado), Padrón (versión + entradas), Calificación (numérica/textual,
aprobado derivado), Umbral por materia, Slot/Instancia de Encuentro, Guardia, Tarea + ComentarioTarea, Aviso +
AcknowledgmentAviso, Evaluación + Reserva + Resultado, FechaAcadémica, ProgramaMateria, SalarioBase/SalarioPlus,
Liquidación, Factura, Comunicación (cola), AuditLog. (Detalle completo en el fulltext §04.)

Roles que liquidan con Base: COORDINADOR, NEXO, PROFESOR, TUTOR. Plus por **categoría de materia × rol** (claves tipo `PROG`,`BD`).

---

## 7. Flujos a prototipar (los más valiosos para la demo clickable)
1. **FL-02 Profesor**: login → elegir comisión → importar notas → ver actividades → fijar umbral → ver atrasados/ranking → seleccionar atrasados → preview → encolar.
2. **FL-04 Aprobación**: profesor encola masivo → coordinador entra a la cola → aprueba/cancela (lote o individual) → estados.
3. **FL-03 Setup de cuatrimestre** (ya tengo el wizard) → conectarlo con clonar equipo + padrón.
4. **FL-07 Coloquio**: coordinador crea convocatoria con cupos → alumno reserva turno → seguimiento de cupos.
5. **FL-08 Liquidación** (Finanzas): elegir período → cálculo Base+Plus → preview → exportar → cerrar (inmutable).
6. **FL-01 Login** con 2FA + recuperación, y **cambio de rol** post-login.

---

## 8. Preguntas abiertas que afectan el front (a confirmar con el usuario)
- **PA-25 NEXO**: ¿qué ve/hace exactamente? (define su panel). Hoy sin especificar.
- **PA-01 Materias**: ¿una sola entidad Materia o Materia(plan) + InstanciaDictado? (afecta selectores y monitor).
- **Alcance del MVP del front**: ¿prototipamos los 7 roles o priorizamos COORDINADOR + PROFESOR + ALUMNO + FINANZAS?
- ¿Querés **un solo prototipo con switcher de rol** (recomendado) o un set de pantallas por rol?
- Severidad de avisos, ciclo de vida de Tareas, criterio de clasificación del monitor (PA-08/11/16): usamos defaults razonables salvo que prefieras otros.

---

## 9. Plan propuesto para la fase clickable (cuando retomemos)
1. **Reestructurar a prototipo role-aware**: shell con **switcher de rol** + nav derivado de permisos. (Reusa todo el sistema A.)
2. **Login + 2FA + recuperación** como entrada.
3. Completar/ajustar vistas por épica priorizando los **flujos del §7** (interacciones reales con useState).
4. Agregar lo que falta: **Alumno**, **Finanzas (grilla+facturas)**, **inbox**, **cola/aprobación de comms**, **avisos con ack**, **fechas de evaluación**, **encuentros (forms)**.
5. Ajustes de copy por reglas: padrón destructivo, "Todas las materias", vigencias, inmutabilidad.
6. Tweaks para alternar rol y para mostrar/ocultar estados (vacío vs con datos).
```
Estado actual: vistas estáticas en dirección A (Mockups Activia.html). Próximo: prototipo clickable role-aware.
```
