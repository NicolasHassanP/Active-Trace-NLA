# PRD — activia-trace

**Producto**: activia-trace
**Versión del documento**: 0.2
**Fecha**: 2026-05-28
**Estado**: Draft — requiere validación con stakeholders
**Referencia funcional**: [Base de conocimiento](../knowledge-base/README.md)

---

## TL;DR

**activia-trace** es una **plataforma de gestión académica y trazabilidad de actividades estudiantiles** que opera como capa de inteligencia sobre **Moodle**. Consolida la actividad académica (calificaciones, entregas, padrones) en vistas accionables, detecta y comunica atrasos, coordina equipos docentes y opera liquidaciones de honorarios — todo con trazabilidad completa.

**El nombre lo dice todo**: *activia-trace* = trazabilidad de actividades. La promesa central es que **toda actividad académica relevante quede registrada, atribuida y auditable**, sin fricción para el docente.

---

## 1. Contexto y oportunidad

### 1.1 Contexto

La institución (TUPAD como tenant inicial, escalable a otras carreras e instituciones) usa **Moodle** como LMS. Moodle por sí solo no resuelve:

- Consolidar calificaciones de múltiples actividades por alumno en una vista accionable.
- Detectar y comunicar atrasos masivamente con personalización.
- Coordinar equipos docentes (asignaciones, jerarquías, vigencias) a través de comisiones.
- Operar liquidaciones de honorarios contra la actividad efectiva del docente.
- Mantener trazabilidad institucional de cada acción.

activia-trace cubre esos huecos como una capa que se integra con Moodle (lee calificaciones, padrones y reportes) y agrega encima la inteligencia operativa, la comunicación gobernada y la trazabilidad que la institución necesita.

### 1.2 Objetivos de producto — drivers de diseño

Estos son los principios de diseño que el producto debe cumplir desde su base:

| # | Driver de diseño | Por qué importa |
|---|------------------|-----------------|
| D1 | **Integración automática con Moodle** (Web Services), con fallback de import manual | Datos siempre frescos, sin doble manipulación de archivos |
| D2 | **Historial de padrón auditado**: ningún import sobrescribe el anterior — se versiona | Trazabilidad completa de altas/bajas en cada cohorte |
| D3 | **Catálogo único de materias** por tenant con scoping por carrera/cohorte | Elimina divergencia de datos y doble carga manual |
| D4 | **Portal del alumno** con vista consolidada de su propio estado | El alumno es participante activo, no objeto pasivo del sistema |
| D5 | **API REST pública con OpenAPI 3.1** | Habilita integraciones con otras plataformas (RRHH, BI, ecosistema) |
| D6 | **Stack desacoplado y moderno** con separación de responsabilidades | Fácil de escalar, testear y evolucionar con bus factor razonable |
| D7 | **Dashboards analíticos** además de vistas operativas | Detección de tendencias y predicción de abandono |
| D8 | **Nomenclatura y datos consistentes** desde el seed hasta la UI | Calidad de datos como requisito no negociable |
| D9 | **Audit log sin límite**, con búsqueda full-text y rangos largos | Investigación de incidentes sin restricciones arbitrarias |
| D10 | **Modelo de roles explícito** con permisos finos por feature | Decisiones de autorización transparentes y verificables |

### 1.3 Capacidades clave que el producto ofrece

Estas capacidades son los diferenciadores funcionales del sistema:

| # | Capacidad | Valor que aporta |
|---|-----------|-----------------|
| K1 | **Preview obligatorio del mail antes del envío** ([RN-16](../knowledge-base/05_reglas_de_negocio.md#rn-16)) | Previene errores comunicacionales caros |
| K2 | **Aprobación humana de mails masivos** ([RN-17](../knowledge-base/05_reglas_de_negocio.md#rn-17)) | Gobernanza comunicacional, evita spam reputacional |
| K3 | **Audit log de cada acción** con contexto completo ([RN-23](../knowledge-base/05_reglas_de_negocio.md#rn-23)) | Trazabilidad regulatoria robusta |
| K4 | **Scope por (docente, materia) en datos importados** ([RN-04](../knowledge-base/05_reglas_de_negocio.md#rn-04)) | Cada docente trabaja sin pisarle datos a otro |
| K5 | **Clonado de equipos entre cohortes** ([RN-12](../knowledge-base/05_reglas_de_negocio.md#rn-12)) | Reduce setup de inicio de cuatrimestre de horas a minutos |
| K6 | **Avisos con scope, severity, vigencia y require_ack** ([RN-18..20](../knowledge-base/05_reglas_de_negocio.md#rn-18--avisos-tienen-ventana-de-vigencia)) | Comunicación institucional con trazabilidad |
| K7 | **Vigencia temporal por asignación** ([RN-10](../knowledge-base/05_reglas_de_negocio.md#rn-10)) | Permite rotación natural entre periodos |
| K8 | **Estados del worker de comunicaciones** ([RN-15](../knowledge-base/05_reglas_de_negocio.md#rn-15)) | Visibilidad operativa de la cola |
| K9 | **Umbral configurable por docente × materia** ([RN-03](../knowledge-base/05_reglas_de_negocio.md#rn-03)) | Respeta criterio pedagógico individual |
| K10 | **Detección de TPs entregados sin corregir** ([RN-07](../knowledge-base/05_reglas_de_negocio.md#rn-07)) | Killer-feature: cierra el ciclo docente sin fricción |

---

## 2. Visión y North Star

### 2.1 Visión

> **"Que ningún alumno se pierda y ningún docente se quede atrás por falta de información."**

activia-trace es la **capa de inteligencia operativa** entre Moodle y el día a día del equipo docente. Convierte la actividad cruda del LMS en **decisiones accionables** y deja **trazabilidad completa** de cada una.

### 2.2 North Star Metric

**% de alumnos atrasados que recibieron un recordatorio dentro de 48hs de detectado el atraso.**

Justificación: combina detección efectiva (que el sistema detecte rápido) + ejecución (que el docente reciba la alerta y actúe) + impacto (que el alumno reciba la comunicación). Mide el ciclo completo end-to-end del valor del producto.

### 2.3 Secondary metrics

- **MTTR** de detección de TP sin corregir (desde entrega del alumno hasta que el docente lo ve listado).
- **Email delivery rate** (% en estado OK del total enviado).
- **% de cohorte cubierta** por avisos `require_ack` confirmados.
- **Tiempo promedio de setup de cuatrimestre nuevo** (alta de cohorte + clonado de equipos + carga inicial).
- **% de docentes activos** en la última semana (login + ≥1 import o ≥1 acción registrada).

---

## 3. Audiencia / Personas

> Las personas se derivan directamente de los [actores del sistema](../knowledge-base/03_actores_y_roles.md). Ampliamos con JTBD (Jobs To Be Done).

### Persona 1 — Profesor de comisión

- **Rol**: PROFESOR
- **Contexto**: maneja entre 1 y 4 comisiones simultáneas en TUPAD. Dicta clase asincrónica + encuentros sincrónicos semanales. Cobra honorarios mensuales por la institución.
- **Jobs**:
  - "Cuando termino una semana de cursado, quiero saber **quién quedó descolgado** sin perder media hora cruzando Moodle a mano."
  - "Cuando subo notas, quiero **detectar lo que entregaron pero no califiqué** para no quedar mal."
  - "Cuando mando recordatorios, quiero **estar seguro de que el mail se ve bien** antes de apretar enviar."
- **Pains que el producto elimina**:
  - La doble manipulación de archivos (exportar de Moodle, descargar, subir, parsear).
  - La falta de visión consolidada al instante.
  - El riesgo de "perder" su trabajo si no carga el padrón al día.

### Persona 2 — Coordinador académico

- **Rol**: COORDINADOR
- **Contexto**: responsable de un conjunto de materias o de una cohorte completa. Asigna profesores, sigue rendimiento, decide medidas pedagógicas.
- **Jobs**:
  - "Cuando arranca un cuatrimestre, quiero **clonar el equipo del anterior** y solo ajustar deltas."
  - "Cuando hay un alumno en riesgo, quiero **ver el panorama completo** (todas las materias, todos los docentes que lo tocan)."
  - "Cuando un docente está inactivo, quiero **detectarlo antes de que sea problema**."
- **Pains que el producto elimina**:
  - El monitoreo plano sin segmentación inteligente ni alertas proactivas.
  - La falta de vista cruzada del alumno (ver al alumno X en todas sus materias).
  - El log de acciones truncado.

### Persona 3 — Administrador del sistema

- **Rol**: ADMIN
- **Jobs**:
  - "Quiero **dar de alta una nueva cohorte** sin tener que repetir 100 asignaciones."
  - "Quiero **auditar quién hizo qué** ante cualquier reclamo académico."
  - "Quiero **aprobar/rechazar envíos masivos** antes de que salgan."
- **Pains que el producto elimina**:
  - El ABM repetitivo de carreras/cohortes/programas.
  - Los permisos confusos: el ADMIN tiene permisos finos explícitos, no un flag binario opaco.

### Persona 4 — Admin financiero / Liquidaciones

- **Rol**: FINANZAS
- **Jobs**:
  - "A fin de mes, quiero **generar la liquidación de todo el equipo** y exportar el listado para el pago bancario."
  - "Quiero **inmutabilizar** la liquidación una vez aprobada para que nadie la modifique."
- **Pains que el producto elimina**:
  - La fórmula de cálculo opaca (ver [PA-06](../knowledge-base/10_preguntas_abiertas.md#pa-06)) → fórmula transparente y testeable.
  - La falta de un flujo claro de revisión + cierre.

### Persona 5 — Alumno

- **Rol**: ALUMNO
- **Contexto**: cursa entre 4 y 6 materias en paralelo en TUPAD, vive en distintas regionales del país.
- **Jobs**:
  - "Quiero **ver mi estado consolidado** en todas las materias sin entrar a Moodle materia por materia."
  - "Quiero **reservar lugar en un coloquio** sin esperar mail del docente."
  - "Quiero **recibir avisos importantes** en un solo lugar."
- **Pains que el producto elimina**: la dependencia total del docente para enterarse de su propio estado.

### Persona 6 — Tutor / Ayudante

- **Rol**: TUTOR
- **Jobs**:
  - "Quiero registrar las **guardias** que cubro."
  - "Quiero ver los **alumnos asignados a mí** en cada materia."
- **Pains que el producto elimina**: permisos opacos — el rol TUTOR tiene capacidades explícitas y acotadas.

---

## 4. Goals & Non-Goals

### 4.1 Goals (MVP + visión)

#### G1 — Cobertura funcional completa del ciclo docente en el MVP
Todo el ciclo operativo del docente (importar, ver atrasados, enviar mails con preview, gestionar encuentros) **debe estar cubierto en el MVP**.

#### G2 — Integración automática con Moodle (no upload manual)
Eliminar la fricción del "exportá Excel, subilo, parseá". Conectar vía **Moodle Web Services / OAuth2** para tomar calificaciones, padrones y reportes **en background**, con import manual como respaldo.

#### G3 — Un solo catálogo de materias
**Un solo catálogo de materias** por tenant, con historial de padrón y modelo de roles claro. Elimina duplicación y divergencia de datos.

#### G4 — Multi-tenancy real
Aislar instituciones como tenants independientes para escalar más allá de TUPAD.

#### G5 — Trazabilidad total
Toda acción significativa auditada, sin límites de retención en la UI.

### 4.2 Non-Goals (explícitos)

#### NG1 — Reemplazar a Moodle
Moodle sigue siendo el LMS oficial. activia-trace es la capa de inteligencia operativa. No alojamos contenidos pedagógicos ni recibimos entregas.

#### NG2 — Ser un corrector automático
La corrección automática de trabajos queda fuera del alcance. Podría integrarse en Fase 2+ como módulo externo.

#### NG3 — Gestión de pagos/transferencias
Calculamos liquidaciones y exportamos. No ejecutamos pagos bancarios.

---

## 5. Métricas de éxito

| Categoría | Métrica | Target |
|-----------|---------|--------|
| Adopción | % docentes activos semanalmente | > 80% |
| Eficiencia | Tiempo de setup de cuatrimestre | < 30 min |
| Calidad | % alumnos atrasados contactados < 48hs | > 90% |
| Performance | P95 de respuesta API | < 500 ms |
| Performance | Import Moodle (100 alumnos × 30 act.) | < 30 s |
| Confiabilidad | Uptime mensual | ≥ 99.5% |
| Comunicación | Email delivery rate | > 95% |

---

## 6. Requirements

Requirements numerados como **RF-XX** (funcional) y **RNF-XX** (no funcional). Cada uno está vinculado a las [HUs de la KB](../knowledge-base/11_historias_de_usuario.md) cuando aplica.

### 6.1 Requirements funcionales — MVP (Fase 1)

#### Auth, Roles y Tenants

> 🔐 **Principio de seguridad fundamental**: la identidad y el tenant de un usuario se derivan **EXCLUSIVAMENTE** de su sesión autenticada (JWT verificado). Ningún parámetro de la petición (URL, body, header) puede alterar quién es el usuario ni qué permisos tiene. Diseño completo en [`ARQUITECTURA.md` §5 Seguridad](./ARQUITECTURA.md).

- **RF-01** — Login con email + password + 2FA opcional (TOTP). Resuelve [PA-04](../knowledge-base/10_preguntas_abiertas.md#pa-04). [HU-45](../knowledge-base/11_historias_de_usuario.md#hu-45--login-del-usuario)
- **RF-02** — Recuperación de contraseña por email con token de un solo uso.
- **RF-03** — Multi-tenancy: cada institución es un tenant aislado. Datos jamás cruzan.
- **RF-04** — Modelo de roles claro: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS. **Permisos finos por feature** (no flag binario de superusuario): cada acción protegida exige un permiso explícito.
- **RF-05** — Audit log de TODO login, logout, cambio de contraseña, cambio de rol e inicio/fin de impersonación.

#### Ingesta y Datos

- **RF-06** — Integración con Moodle vía **Web Services** (funciones `core_grades_get_grades`, `core_user_get_users_by_field`, etc.). Sync nocturna automática + sync on-demand.
- **RF-07** — Fallback: import manual de `.xlsx`/`.csv` para casos sin acceso a Moodle Web Services. [HU-01](../knowledge-base/11_historias_de_usuario.md#hu-01---importar-calificaciones-por-materia)
- **RF-08** — Detección de columnas `(Real)` para notas numéricas ([RN-01](../knowledge-base/05_reglas_de_negocio.md#rn-01)).
- **RF-09** — Mapeo de escala textual ("Satisfactorio", "Supera lo esperado") con catálogo configurable por tenant ([RN-02](../knowledge-base/05_reglas_de_negocio.md#rn-02)).
- **RF-10** — **Padrón con historial**: ningún import borra el anterior — se versiona con timestamp. Permite auditar altas/bajas en cualquier cohorte. [HU-03](../knowledge-base/11_historias_de_usuario.md#hu-03---importar-padrón-de-alumnos)
- **RF-11** — **Catálogo único de materias** por tenant — un solo dataset con scoping por carrera/cohorte. Elimina duplicación y divergencia de datos.

#### Análisis y Reportes

- **RF-12** — Umbral configurable por docente × materia (default 60%). [HU-05](../knowledge-base/11_historias_de_usuario.md#hu-05---configurar-umbral-de-aprobación-por-materia)
- **RF-13** — Lista de atrasados (faltantes O nota < umbral). [HU-06](../knowledge-base/11_historias_de_usuario.md#hu-06---ver-lista-de-alumnos-atrasados)
- **RF-14** — Ranking de aprobadas (excluyendo alumnos sin actividad). [HU-07](../knowledge-base/11_historias_de_usuario.md#hu-07---ver-ranking-de-alumnos-por-aprobadas)
- **RF-15** — Notas finales agrupadas exportables a hoja de cálculo. [HU-08](../knowledge-base/11_historias_de_usuario.md#hu-08---generar-notas-finales-agrupadas-para-excel)
- **RF-16** — Detección de TP entregados sin corregir, filtrable y exportable. [HU-02](../knowledge-base/11_historias_de_usuario.md#hu-02---detectar-entregas-finalizadas-sin-corregir)

#### Comunicación

- **RF-17** — Preview obligatorio del mail antes del envío (Asunto + HTML render). [HU-10](../knowledge-base/11_historias_de_usuario.md#hu-10---previsualizar-mail-antes-de-enviarlo)
- **RF-18** — Cola de comunicaciones con estados Pend/Send/OK/Fail/Canc. [HU-11](../knowledge-base/11_historias_de_usuario.md#hu-11---enviar-recordatorios-masivos-a-alumnos-atrasados)
- **RF-19** — Aprobación humana opcional (configurable por tenant): si está activa, envíos masivos requieren aprobación. [HU-12](../knowledge-base/11_historias_de_usuario.md#hu-12---aprobar-mails-masivos-antes-de-despacho)
- **RF-20** — Plantillas de mail con variables tipo `{{alumno.nombre}}`, `{{materia.nombre}}`, etc., editables por COORDINADOR.
- **RF-21** — Avisos del sistema (tablón) con scope (global/materia/cohorte), severity, role_target, vigencia, sort, require_ack. [HU-14](../knowledge-base/11_historias_de_usuario.md#hu-14---publicar-aviso-del-sistema-con-scope-y-vigencia)
- **RF-22** — Mensajería interna docente ↔ coordinación (threads + responder). [HU-13](../knowledge-base/11_historias_de_usuario.md#hu-13---recibir-y-responder-mensajes-internos)

#### Equipos Docentes y Estructura Académica

- **RF-23** — ABM de carreras, cohortes, materias, profesores. [HU-16](../knowledge-base/11_historias_de_usuario.md#hu-16---dar-de-alta-un-profesor), [HU-21](../knowledge-base/11_historias_de_usuario.md#hu-21---administrar-carreras), [HU-22](../knowledge-base/11_historias_de_usuario.md#hu-22---administrar-cohortes)
- **RF-24** — Asignaciones individuales y masivas profesor↔materia con vigencia y jerarquía (`responde_a`). [HU-18](../knowledge-base/11_historias_de_usuario.md#hu-18---asignar-masivamente-docentes-a-una-materia)
- **RF-25** — Clonado de equipo entre cohortes. [HU-19](../knowledge-base/11_historias_de_usuario.md#hu-19---clonar-equipo-docente-entre-cohortes)
- **RF-26** — Modificar vigencia general de un equipo en bloque. [HU-20](../knowledge-base/11_historias_de_usuario.md#hu-20---modificar-vigencia-general-de-un-equipo)
- **RF-27** — Subida de programas (PDF) por materia × carrera × cohorte. [HU-23](../knowledge-base/11_historias_de_usuario.md#hu-23---subir-programa-de-materia-pdf)
- **RF-28** — Calendario académico con fechas de parciales, TP y coloquios. [HU-24](../knowledge-base/11_historias_de_usuario.md#hu-24---gestionar-fechas-de-parcialestpcoloquios)

#### Encuentros y Disponibilidad

- **RF-29** — Slots de encuentro recurrentes con generación automática de N instancias. [HU-25](../knowledge-base/11_historias_de_usuario.md#hu-25---crear-slot-de-encuentro-recurrente)
- **RF-30** — Encuentros únicos (no recurrentes). [HU-26](../knowledge-base/11_historias_de_usuario.md#hu-26---crear-encuentro-único-no-recurrente)
- **RF-31** — Edición de instancia individual (estado, meet, video, comentario). [HU-27](../knowledge-base/11_historias_de_usuario.md#hu-27---editar-instancia-individual-de-encuentro)
- **RF-32** — Snippet HTML exportable para pegar en Moodle. [HU-28](../knowledge-base/11_historias_de_usuario.md#hu-28---generar-cronograma-de-encuentros-embebible-en-el-lms)
- **RF-33** — Registro de guardias con form de alta. Resuelve [PA-05](../knowledge-base/10_preguntas_abiertas.md#pa-05). [HU-29](../knowledge-base/11_historias_de_usuario.md#hu-29---ver-mis-guardias-realizadas), [HU-46](../knowledge-base/11_historias_de_usuario.md#hu-46---crear-una-guardia)

#### Coloquios

- **RF-34** — Convocatoria a coloquio (instancia + días + cupos). [HU-31](../knowledge-base/11_historias_de_usuario.md#hu-31---crear-nueva-convocatoria-de-coloquio)
- **RF-35** — Reservas de alumnos con cupos auto-decreciendo.
- **RF-36** — Agenda admin consolidada de reservas. [HU-32](../knowledge-base/11_historias_de_usuario.md#hu-32---ver-agenda-consolidada-de-reservas)

#### Tareas internas

- **RF-37** — Workflow profesor ↔ coordinación con estados + comentarios. [HU-34](../knowledge-base/11_historias_de_usuario.md#hu-34---ver-mis-tareas-asignadas), [HU-36](../knowledge-base/11_historias_de_usuario.md#hu-36---administrar-todas-las-tareas-coordinación)

#### Auditoría

- **RF-38** — Audit log persistente sin límite, con búsqueda full-text por código de acción, usuario, materia, rango de fechas, IP. Sin restricciones arbitrarias de retención. [HU-38](../knowledge-base/11_historias_de_usuario.md#hu-38---auditar-acciones-individuales)
- **RF-39** — Panel de interacciones por docente con filtros y exportación. [HU-37](../knowledge-base/11_historias_de_usuario.md#hu-37---ver-panel-de-interacciones-por-docente)
- **RF-40** — Webhooks de eventos (acciones críticas) para integraciones externas.

#### Liquidaciones

- **RF-41** — Grilla de salarios editable por rol y otros ejes configurables. [HU-41](../knowledge-base/11_historias_de_usuario.md#hu-41---mantener-la-grilla-de-salarios)
- **RF-42** — Cálculo de liquidación = Base + Plus, con fórmula transparente, documentada y testeable. Resuelve [PA-06](../knowledge-base/10_preguntas_abiertas.md#pa-06). [HU-39](../knowledge-base/11_historias_de_usuario.md#hu-39---ver-vista-previa-de-liquidación-del-período)
- **RF-43** — Cerrar liquidación = inmutabilizar período. [HU-40](../knowledge-base/11_historias_de_usuario.md#hu-40---cerrar-liquidación-de-un-período)
- **RF-44** — Historial completo de liquidaciones por docente.

#### Perfil

- **RF-45** — Editar datos personales y bancarios. [HU-42](../knowledge-base/11_historias_de_usuario.md#hu-42---editar-mis-datos-personales-y-bancarios)
- **RF-46** — Logout (revoca el refresh token y descarta el access JWT). [HU-43](../knowledge-base/11_historias_de_usuario.md#hu-43---cerrar-sesión)

#### Facturación de monotributistas

- **RF-61** — Docente monotributista (flag `facturador=true`) puede subir factura mensual en PDF con detalle libre. [HU-49](../knowledge-base/11_historias_de_usuario.md#hu-49---docente-sube-su-factura-mensual)
- **RF-62** — Admin gestiona facturas con filtros (docente, estado pendiente/abonada, rango de fechas), marca como abonada y descarga PDFs. Las facturas NO se incluyen en la liquidación general — sustituyen al cálculo Base+Plus. [HU-48](../knowledge-base/11_historias_de_usuario.md#hu-48---gestionar-facturas-de-docentes-monotributistas)
- **RF-63** — Reglas de negocio confirmadas: NEXO suma al total pero se muestra aparte; monotributistas se segregan completamente; liquidación se opera por (cohorte × mes); ABM de grilla Base + grilla Plus con vigencia abierta. Ver [RN-31..40](../knowledge-base/05_reglas_de_negocio.md#dominio-liquidaciones-y-salarios).

### 6.2 Requirements funcionales — Fase 2

#### Portal del Alumno

- **RF-47** — Login alumno con SSO institucional (Moodle SSO ideal).
- **RF-48** — Vista consolidada: estado del alumno en TODAS sus materias.
- **RF-49** — Self-service: reserva de coloquios, ACK de avisos, descarga de programas. [HU-47](../knowledge-base/11_historias_de_usuario.md#hu-47---alumno-reserva-un-coloquio)
- **RF-50** — Notificaciones push (web) al alumno.

#### Analytics y BI

- **RF-51** — Dashboard de tendencias (atrasados por cohorte vs tiempo, distribución de notas, etc.).
- **RF-52** — Predicción de abandono ML-driven (riesgo alto/medio/bajo por alumno).
- **RF-53** — Reportes ejecutivos exportables PDF/Excel.

#### API y Ecosistema

- **RF-54** — API REST pública documentada con OpenAPI 3.1. Habilita integraciones con otras plataformas.
- **RF-55** — Webhooks suscribibles para eventos clave.
- **RF-56** — Integraciones nativas: Google Workspace (Calendar para encuentros), Slack (notificaciones).

### 6.3 Requirements funcionales — Fase 3+

- **RF-57** — App móvil (PWA primero, luego nativa según adopción).
- **RF-58** — Mensajería real-time (chat docente↔alumno).
- **RF-59** — Integración con AFIP (factura electrónica para monotributistas).
- **RF-60** — Multi-idioma (i18n).

### 6.4 Requirements no funcionales

#### Performance y Escalabilidad

- **RNF-01** — P95 de respuesta API < 500 ms para listados, < 2s para reportes.
- **RNF-02** — Soporte ≥ 10.000 usuarios concurrentes con elasticidad horizontal.
- **RNF-03** — Import Moodle de 100 alumnos × 30 actividades en < 30s.

#### Disponibilidad

- **RNF-04** — Uptime mensual ≥ 99.5%.
- **RNF-05** — RPO ≤ 1h, RTO ≤ 4h.
- **RNF-06** — Backups diarios + retención 30 días.

#### Seguridad

- **RNF-07** — Todo tráfico HTTPS con TLS 1.3.
- **RNF-08** — Datos sensibles (CBU, DNI) cifrados en reposo (AES-256).
- **RNF-09** — Auth con JWT corto (15min) + refresh token rotation. La identidad se deriva solo del JWT verificado.
- **RNF-10** — CSRF protection en endpoints state-changing.
- **RNF-11** — Rate limiting por IP y por usuario.
- **RNF-12** — Audit log inmutable (append-only, idealmente write-once storage).
- **RNF-13** — Cumplir Ley 25.326 Argentina (Datos Personales).
- **RNF-14** — Pentest anual + bug bounty.

#### Mantenibilidad

- **RNF-15** — Coverage de tests ≥ 80% líneas + 90% reglas de negocio.
- **RNF-16** — CI/CD pipeline (build + test + lint + deploy automatizado).
- **RNF-17** — Logs estructurados (JSON) + observability (OpenTelemetry).
- **RNF-18** — Feature flags para rollouts graduales.

#### UX

- **RNF-19** — Responsive desde 360px hasta 4K.
- **RNF-20** — WCAG 2.1 AA mínimo.
- **RNF-21** — Tiempo de aprendizaje del docente nuevo < 30 min para flujo principal.

#### Multi-tenancy

- **RNF-22** — Aislamiento total de datos por tenant (database-level si es factible, row-level mínimo).
- **RNF-23** — Configuración por tenant: idioma, branding, plantillas de mail, catálogo de escalas.

---

## 7. Scope: MVP vs Fases

### 7.1 MVP (Fase 1) — meta 3 a 4 meses

**Objetivo**: cubrir el ciclo operativo completo del docente + base limpia para escalar. Adoptable por docentes desde día 1.

Incluye RF-01 a RF-46 + RF-61..63 + RNF-01 a RNF-23.

**Excluye explícitamente**:
- Portal del alumno
- Dashboards analíticos avanzados
- API pública (solo interna)
- App móvil
- ML / predicción

### 7.2 Fase 2 — Portal del alumno + Analytics — meta +3 meses post-MVP

Incluye RF-47 a RF-56.

### 7.3 Fase 3+ — Móvil + Real-time + Ecosistema

Incluye RF-57 a RF-60.

---

## 8. User Journeys clave (MVP)

> Los journeys completos están en [07_flujos_principales.md](../knowledge-base/07_flujos_principales.md). Acá los resumimos como el flow esperado del producto.

### Journey 1 — Profesor detecta atrasados y manda recordatorios

```
1. Profesor → login con 2FA
2. Dashboard "Mi semana": ve KPIs de cada materia (atrasados, sin corregir, próximos parciales)
3. Click en materia X → vista detallada
4. (Background: el sistema ya sincronizó con Moodle automáticamente esa madrugada — RF-06)
5. Sección "Alumnos atrasados" muestra los N detectados
6. Click en "Recordar a todos"
7. Sistema arma N mails personalizados con plantilla
8. Modal de preview muestra los primeros 3 mails
9. Profesor aprueba → cola Pend
10. (Si el tenant tiene aprobación activa) → admin aprueba → Send
11. (Worker) → OK/Fail → métricas visibles
```

**Lo que aporta**: los pasos 4 y 6-7 son automáticos. La sincronización con Moodle ocurre en background y los mails se arman solos — cero manipulación manual de archivos.

### Journey 2 — Coordinador arma nueva cohorte

```
1. Coordinador → "Cohortes" → "Nueva cohorte" → "AGO-2026"
2. Sistema sugiere clonar de la cohorte anterior (MAR-2026)
3. Coordinador acepta → todas las asignaciones se duplican
4. Coordinador ajusta deltas (profes nuevos, materias huérfanas)
5. Sistema confirma OK
6. Coordinador publica aviso de bienvenida con `require_ack`
```

**Lo que aporta**: la sugerencia proactiva de clonado reduce el setup de cuatrimestre a < 30 min.

### Journey 3 — Alumno consulta su estado (Fase 2)

```
1. Alumno → login con SSO Moodle
2. Dashboard: muestra sus 5 materias con barra de progreso
3. Click en materia → ve actividades, calificaciones, faltantes
4. Si hay coloquio con cupos abiertos → CTA "Reservar"
5. Reserva en 2 clicks
6. Recibe confirmación por email + sistema cuenta el cupo
```

**Lo que aporta**: el alumno gestiona su propio estado sin depender del docente.

---

## 9. Modelo de datos (high-level)

> Modelo detallado en [04_modelo_de_datos.md](../knowledge-base/04_modelo_de_datos.md). Acá los pilares estructurales.

### Pilares estructurales del modelo

| Pilar | Por qué |
|-------|---------|
| **Tenant** como primer nivel | Multi-tenancy real (G4); ningún dato cruza tenants |
| **Identidad UUID** (no el legajo como PK) | La identidad nunca se expone ni se selecciona por un parámetro de request; el legajo es atributo de negocio |
| **Padrón versionado** | Historial de altas/bajas, sin upsert destructivo |
| **Catálogo único de materias** | Una sola fuente de verdad por tenant |
| **Roles + permisos finos** (no flag binario) | Authz clara, explícita y auditable |
| **Audit log sin límite** | Trazabilidad regulatoria completa |

---

## 10. Stack tecnológico propuesto

> Detalle completo en [`docs/ARQUITECTURA.md`](./ARQUITECTURA.md). Acá el resumen ejecutivo.

| Capa | Tecnología |
|------|-----------|
| Backend | **FastAPI** + SQLAlchemy 2.0 + Alembic |
| Base de datos | **PostgreSQL** (JSONB para criterios configurables) |
| Frontend | **React 18** + TypeScript + Vite + React Query + Tailwind |
| Auth | **JWT** (access 15min + refresh rotation), Argon2id |
| Infra | **Docker** + Easypanel, N8N para workflows |
| Observabilidad | OpenTelemetry + logs estructurados JSON |

---

## 11. Riesgos y mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| R1 | Moodle WS deshabilitado o sin permisos en algún tenant | Media | Alto | Mantener fallback de import manual ([RF-07](#ingesta-y-datos)) |
| R2 | Carga inicial de datos de un tenant nuevo incompleta o inconsistente | Media | Alto | Validación + reconciliación + período de verificación previo al go-live |
| R3 | Resistencia al cambio de docentes a una herramienta nueva | Media | Medio | Onboarding guiado + cobertura funcional completa desde el MVP |
| R4 | Modelo de materias mal diseñado (¿una entidad o Materia + InstanciaDictado?) | Media | Alto | Resolver [OQ-01](#12-open-questions-a-resolver-antes-de-cerrar-el-prd) **antes** de cerrar el modelo de datos |
| R5 | Complejidad de liquidaciones subestimada | Alta | Medio | Definir fórmula con finanzas en sprint 1, no asumir |
| R6 | Lock-in con un proveedor (auth, cloud) | Baja | Medio | Preferir estándares abiertos (OAuth2, S3 API, OpenTelemetry) |
| R7 | Compliance / Ley 25.326 mal implementado | Baja | Alto | Asesoría legal antes de MVP go-live, cifrado de PII en reposo |
| R8 | Estrategia multi-tenancy elegida mal escala (row-level vs DB-per-tenant) | Media | Alto | Decidir ADR-002 antes de la primera migración de esquema |

---

## 12. Open questions

> Algunas heredadas de la KB ([10_preguntas_abiertas.md](../knowledge-base/10_preguntas_abiertas.md)), otras del PRD.
>
> ⚠️ **Las decisiones de cimiento ya están cerradas** (ver ADR-001/002/006 en [ARQUITECTURA.md §10](./ARQUITECTURA.md)). **El resto de estas open questions se definen DURANTE el desarrollo** — no bloquean el arranque. Cada una se resuelve al llegar a su módulo o cuando el área de negocio correspondiente (FINANZAS, coordinación) aporte la definición. Mientras tanto, el desarrollo del esqueleto (tenant + auth + RBAC + estructura académica) puede avanzar sin esperarlas.

### Heredadas de la KB

- ~~**OQ-01**~~ — ✅ **CERRADA**: modelo **Materia (catálogo único) + Dictado (instancia por carrera×cohorte)**. Ver [ADR-006 en ARQUITECTURA.md §10](./ARQUITECTURA.md).
- **OQ-11** — ¿Cómo se mapean las claves de Plus a familias de materias? — [PA-22](../knowledge-base/10_preguntas_abiertas.md#pa-22).
- **OQ-12** — ¿Cómo se calcula el Plus si un docente tiene N comisiones de la misma clave? — [PA-23](../knowledge-base/10_preguntas_abiertas.md#pa-23).
- **OQ-13** — ¿Cuál es la semántica del rol NEXO (regional, programa, enlace con el alumno)? — [PA-25](../knowledge-base/10_preguntas_abiertas.md#pa-25).

### Específicas del PRD

- ~~**OQ-04**~~ — ✅ **CERRADA**: **auth propio** (email+password+2FA) en el MVP; **Moodle SSO** para alumnos en Fase 2. Ver [ADR-001 en ARQUITECTURA.md §10](./ARQUITECTURA.md).
- **OQ-05** — ¿Quién ejerce el rol FINANZAS hoy? ¿Existe de forma explícita o lo cubre el COORDINADOR?
- **OQ-06** — ¿Hay otros tenants potenciales además de TUPAD? Si sí, ¿en qué horizonte? Impacta priorización de G4.
- **OQ-07** — ¿La institución tiene presupuesto para hosting cloud o requiere self-host?
- **OQ-08** — ¿Cuál es la estrategia de go-live? ¿Convivencia con sistemas anteriores o reemplazo limpio? Impacta R2 y el período de transición.
- **OQ-09** — ¿Quién aprueba el envío de mails masivos en MVP? Sin esa pregunta resuelta, RF-19 queda incompleto.
- **OQ-10** — ¿La corrección automática de trabajos queda como módulo externo separado o se incluye en Fase 2?

---

## 13. Apéndices

### A — Trazabilidad PRD → KB

| Requirement | KB Reference |
|-------------|--------------|
| RF-01..05 | [03_actores_y_roles](../knowledge-base/03_actores_y_roles.md), [HU-45](../knowledge-base/11_historias_de_usuario.md#hu-45--login-del-usuario) |
| RF-06..11 | [Épica 1 — Ingesta de Datos desde el LMS](../knowledge-base/06_funcionalidades.md#épica-1--ingesta-de-datos-desde-el-lms) |
| RF-12..16 | [Épica 2 — Análisis](../knowledge-base/06_funcionalidades.md) |
| RF-17..22 | [Épica 3 — Comunicación](../knowledge-base/06_funcionalidades.md) |
| RF-23..28 | [Épica 4 + 5 — Equipos y Estructura](../knowledge-base/06_funcionalidades.md) |
| RF-29..33 | [Épica 6 — Encuentros](../knowledge-base/06_funcionalidades.md) |
| RF-34..36 | [Épica 7 — Coloquios](../knowledge-base/06_funcionalidades.md) |
| RF-37 | [Épica 8 — Tareas](../knowledge-base/06_funcionalidades.md) |
| RF-38..40 | [Épica 9 — Auditoría](../knowledge-base/06_funcionalidades.md) |
| RF-41..44 | [Épica 10 — Liquidaciones](../knowledge-base/06_funcionalidades.md) |
| RF-45..46 | [Épica 11 — Perfil](../knowledge-base/06_funcionalidades.md) |
| RF-61..63 | [Épica 13 — Facturación monotributistas](../knowledge-base/11_historias_de_usuario.md) |

### B — Glosario

| Término | Definición |
|---------|-----------|
| **Moodle** | LMS open-source que la institución usa como sistema oficial; fuente de calificaciones, padrones y reportes |
| **Moodle WS** | Moodle Web Services — API estándar de Moodle para integración programática |
| **TUPAD** | Tecnicatura Universitaria en Programación a Distancia — primer tenant |
| **Tenant** | Institución aislada dentro del sistema; sus datos nunca cruzan con otra |
| **RBAC** | Role-Based Access Control — autorización por roles con permisos finos |
| **MTTR** | Mean Time To Resolution |
| **JTBD** | Jobs To Be Done — framework de definición de oportunidades |
| **ADR** | Architecture Decision Record — documento por decisión técnica |
| **PII** | Personally Identifiable Information |
| **PWA** | Progressive Web App |

### C — Historial de cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-05-28 | 0.1 | Draft inicial |
| 2026-05-28 | 0.2 | Documento autocontenido y agnóstico; modelo Auth + RBAC + multi-tenant; Moodle como LMS |

---

## Siguiente paso recomendado

1. **Revisar este PRD con stakeholders** (dueño del producto, COORDINADOR académico, FINANZAS, IT).
2. **Cerrar las Open Questions** (especialmente OQ-01 que bloquea el modelo de datos, y OQ-11/12/13 que bloquean liquidaciones).
3. **Definir métricas baseline** (cuántos atrasados se detectan hoy, cuánto tarda el setup, etc.) para medir el impacto del MVP.
