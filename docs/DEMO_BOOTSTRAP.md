# Demo Bootstrap — Guía para testear en local

Esta guía explica cómo levantar el entorno de desarrollo con datos de demo listos para testear. Seguí los pasos **en orden** cada vez que recreés los contenedores o arrancés en una máquina nueva.

---

## Requisitos previos

- Docker Desktop corriendo
- Node.js 18+ (para el frontend Vite)
- Estar en la rama correcta y con el código actualizado (`git pull`)

---

## 1. Levantar los servicios Docker

```bash
docker compose up -d
```

Esperá a que el healthcheck de postgres esté `healthy`:

```bash
docker compose ps
```

---

## 2. Correr las seeds de demo

Las seeds crean la estructura académica, usuarios y permisos RBAC. **Son idempotentes** — podés correrlas más de una vez sin problema.

```bash
docker cp backend/seed_rbac_demo.py active-trace-api-1:/app/
docker cp backend/seed_demo_users.py active-trace-api-1:/app/
docker cp backend/seed_demo_estructura.py active-trace-api-1:/app/

docker exec active-trace-api-1 sh -c "cd /app && python seed_rbac_demo.py && python seed_demo_users.py && python seed_demo_estructura.py"
```

---

## 3. Levantar el frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend queda en `http://localhost:5173`.

---

## 4. Importar datos de demo (padrón + calificaciones)

Este paso es **necesario** para que los módulos de Calificaciones, Atrasados y Análisis tengan datos. Hacelo una sola vez después de correr las seeds.

### 4.1 Importar el padrón

1. Ir a `http://localhost:5173` e iniciar sesión como **profesor** (ver credenciales abajo)
2. Navegar a **Padrón**
3. Seleccionar **Análisis Matemático I · 2026-1C** en el selector de materia/cohorte
4. Subir `backend/fixtures/padron_demo.csv`
5. Revisar el preview (10 alumnos) y hacer click en **Confirmar importación**

### 4.2 Importar calificaciones

1. Navegar a **Calificaciones**
2. Seleccionar **Análisis Matemático I · 2026-1C**
3. En el tab **Importar**, subir `backend/fixtures/calificaciones_demo.csv`
4. Verificar que detecta 4 actividades: `TP1`, `TP2`, `Parcial 1`, `Trabajo Práctico Final`
5. Hacer click en **Importar 4 actividad(es)**
6. El toast debe decir "Importación exitosa: 40 calificaciones guardadas"

> **Importante**: cada vez que se re-importa el padrón (se sube el CSV nuevamente), hay que re-importar también las calificaciones. El sistema versiona el padrón y las calificaciones deben estar vinculadas a la versión activa.

---

## 5. Credenciales de demo

| Rol | Email | Contraseña |
|-----|-------|-----------|
| Alumno | `alumno@demo.com` | `Demo1234!` |
| Tutor | `tutor@demo.com` | `Demo1234!` |
| Profesor | `profesor@demo.com` | `Demo1234!` |
| Coordinador | `coordinador@demo.com` | `Demo1234!` |
| Admin | `admin@demo.com` | `Admin1234!` |

---

## 6. Qué debería funcionar después del bootstrap

| Módulo | URL | Estado esperado |
|--------|-----|----------------|
| Mis materias | `/materias` | Muestra Análisis Matemático I · 2026-1C |
| Padrón | `/padron` | Selector de materia cargado |
| Calificaciones → Importar | `/calificaciones` | Subir CSV y confirmar |
| Calificaciones → Ranking | `/calificaciones` tab Ranking | 10 alumnos con actividades aprobadas |
| Calificaciones → Notas finales | `/calificaciones` tab Notas finales | Grupos de alumnos con notas |
| Atrasados | `/atrasados` | 10 alumnos únicos con nombres, emails y actividades faltantes |
| Avisos | `/avisos` | Página carga sin errores |
| Mensajes | `/mensajes` | Página carga sin errores |

---

## Troubleshooting

**El selector de materia no carga / aparece vacío**

Las páginas hacen una request a `GET /api/v1/perfil/mis-asignaciones` al cargar. Si ves un error 401/403, la sesión expiró — volvé a hacer login.

**Atrasados muestra `—` en nombre/email**

Significa que las calificaciones están vinculadas a una versión vieja del padrón. Re-importá las calificaciones siguiendo el paso 4.2.

**Los contenedores se recrearon y las seeds ya no están**

Las seeds no corren automáticamente. Repetí el paso 2 completo.

**`docker compose up` falla en el healthcheck de postgres**

Esperá unos segundos y volvé a correr `docker compose ps`. Si sigue fallando:

```bash
docker compose down -v   # ⚠️ borra los volúmenes (perderás los datos)
docker compose up -d
```

Y luego empezá desde el paso 2.

---

## Reset de datos para grabar la demo

Hay dos scripts de reset según cómo quieras arrancar el video. Ambos son idempotentes y, tras correrlos, todos quedan deslogueados (se vacían las sesiones) — volvé a iniciar sesión.

### Opción A — "default/en blanco" (construir todo en vivo)

Deja SOLO los 5 usuarios + RBAC; estructura, asignaciones, padrón, calificaciones y todo lo transaccional quedan vacíos. Pensado para mostrar el flujo completo desde cero (crear carrera/materia/cohorte vía `/admin/estructura`, asignar docentes, importar padrón/calificaciones, etc.).

```bash
docker exec -i active-trace-postgres-1 psql -U postgres -d activia_trace -v ON_ERROR_STOP=1 < backend/reset_demo_blank.sql
```

**Conserva**: tenant, RBAC, los 5 usuarios demo. **Borra**: TODO lo demás (estructura, asignaciones, padrón, calificaciones, umbral, tareas, encuentros, coloquios, mensajería, avisos, comunicaciones, audit log, sesiones).

> Requiere `/admin/estructura` (C-29) para recrear materias/carreras desde la UI. Para repoblar la estructura base sin UI: `python seed_demo_estructura.py` (carrera TDS + 2 materias + cohorte 2026-1C + asignaciones demo).

### Opción B — "demo-ready" (con datos pre-cargados)

Conserva estructura + asignaciones + padrón + calificaciones; solo limpia el junk transaccional. Para arrancar el video con datos ya cargados (Calificaciones/Atrasados muestran info).

```bash
docker exec -i active-trace-postgres-1 psql -U postgres -d activia_trace -v ON_ERROR_STOP=1 < backend/reset_demo_data.sql
```

**Conserva**: tenant, RBAC, 5 usuarios, carrera/materia/cohorte, asignaciones, padrón y calificaciones. **Borra**: tareas, encuentros, coloquios/evaluaciones, mensajería, avisos, comunicaciones, audit log y sesiones.

> Estado 100% pristino desde cero (recrear schema incluido): `docker compose down -v` + migraciones + seeds (ver Troubleshooting + pasos 2 y 4).
