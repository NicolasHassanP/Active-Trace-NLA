# Testing Coordinador — Sesión 2026-06-07

Credenciales: `coordinador@demo.com` / `Demo1234!`

---

## Testeado y funcionando ✅

| Sección | Qué se probó | Resultado |
|---------|-------------|-----------|
| **Login** | Ingreso con credenciales del coordinador | OK — aterriza en dashboard |
| **Padrón** (`/padron`) | Selector materia+cohorte, formulario de importación CSV, secciones Moodle y Vaciar | OK — muestra correctamente al seleccionar materia |
| **Atrasados** (`/atrasados`) | Selector materia+cohorte, estado sin calificaciones | OK — muestra banner "sin datos suficientes" cuando no hay umbral/calificaciones |
| **Seguimiento** (`/seguimiento`) | Selector materia+cohorte, carga de 10 alumnos con nombre real | OK — muestra nombre y apellido, estado, aprobadas, faltantes |
| **Seguimiento — filtros** | Búsqueda por nombre/apellido, filtro Comisión parcial, filtro Regional parcial | OK — todos reactivos con debounce 300ms |
| **Calificaciones** (`/calificaciones`) | Configurar umbral, importar CSV de calificaciones | OK — umbral configurado y calificaciones importadas correctamente |
| **Comunicaciones** (`/comunicaciones`) | Componer mensaje, encolarlo, tab Historial con envíos propios (C-27) | OK — flujo completo funciona, historial lista estados correctamente |
| **Avisos** (`/avisos`) | Crear y publicar aviso, bandeja, sección mensajes sin leer | OK — publicación y bandeja funcionan |

---

## Bugs encontrados y fixeados 🔧

| Bug | Dónde | Fix aplicado |
|-----|-------|-------------|
| Toast decía `"undefined filas importadas"` al activar padrón | `PadronImportForm.tsx` + `padron/types/index.ts` | El backend devuelve `filas_total`, el frontend buscaba `total_filas`. Corregido el tipo y el mensaje. |
| Búsqueda solo filtraba por `nombre`, ignoraba `apellidos` | `analisis_repository.py` | Se agregó `apellidos` al `OR` del ILIKE. |
| Filtros de Comisión y Regional eran match exacto | `analisis_repository.py` | Cambiados a `ILIKE "%valor%"` para búsqueda parcial. |
| Tabla de Seguimiento no mostraba Comisión ni Regional | `SeguimientoTable.tsx`, `seguimiento/types/index.ts`, `MonitorFila` schema, `analisis_service.py` | Agregados campos `comision` y `regional` al schema backend, al service y a la tabla frontend. |

---

## Falta testear 🔲

### Padrón
- [ ] Importar CSV con datos reales y verificar que el conteo en el toast sea correcto
- [ ] Vaciar padrón y confirmar que Seguimiento queda vacío

### Atrasados (`/atrasados`)
- [ ] Con calificaciones cargadas: confirmar que aparecen alumnos atrasados
- [ ] Seleccionar alumnos y usar "Comunicar a seleccionados"
- [ ] Filtros por comisión y regional

### Monitor (`/monitor`)
- [ ] Verificar que muestra nombre/apellido (misma fix de Seguimiento aplica)
- [ ] Filtros de materia, cohorte, estado

### Mensajería (`/mensajes`)
- [ ] Iniciar un hilo con otro usuario
- [ ] Responder un mensaje
- [ ] Verificar que el nombre del otro participante aparece (no UUID)
- [ ] Deep link `?hilo=<id>` desde notificaciones
- [ ] Badge de campanita suma avisos + mensajes no leídos correctamente
- [ ] Animación de campanita al recibir nuevo mensaje

### Equipos docentes (`/equipos`)
- [ ] Asignar tutor/profesor a una comisión
- [ ] Verificar persistencia tras recargar

### Encuentros (`/encuentros`)
- [ ] Crear un encuentro para una comisión
- [ ] Editar/eliminar un encuentro existente

### Coloquios (`/coloquios`)
- [ ] Crear un coloquio
- [ ] Gestionar inscripciones

### Tareas (`/tareas`)
- [ ] Crear una tarea de seguimiento
- [ ] Marcarla como completada

### Setup cuatrimestre (`/setup-cuatrimestre`)
- [ ] Completar el flujo de setup inicial

### Seguridad transversal
- [ ] Logout y acceso directo a `/padron` → debe redirigir al login
- [ ] Verificar que un COORDINADOR no puede acceder a rutas de ADMIN (`/admin/*`)

---

## Notas de contexto

- **Rama activa**: `style/design-handoff` (sin merge a master todavía — ver `HANDOFF.md`)
- **Tenant Demo**: `8531f634-3f1f-45da-9549-2f801d85c39b`
- **Seed de datos**: correr `seed_demo_users.py` + `seed_demo_estructura.py` + `seed_rbac_demo.py` para restaurar el estado base
- Los alumnos del seed tienen estado "Sin datos" hasta importar calificaciones con umbral configurado
