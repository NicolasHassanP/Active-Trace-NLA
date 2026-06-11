# Análisis CHANGES.md vs Prototipo HTML
> Leído el 2026-06-06 de https://github.com/NicolasHassanP/Active-Trace-NLA

## Estado del roadmap (24 changes)

### ✅ ARCHIVADOS (22/24)
- C-01 foundation-setup
- C-02 core-models-y-tenancy
- C-03 auth-jwt-2fa
- C-04 rbac-permisos-finos (archivado 2026-06-03)
- C-05 audit-log
- C-06 estructura-academica (archivado 2026-06-03)
- C-07 usuarios-y-asignaciones (archivado 2026-06-03)
- C-08 equipos-docentes (archivado 2026-06-04)
- C-09 padron-ingesta-moodle (archivado 2026-06-04)
- C-10 calificaciones-y-umbral (archivado 2026-06-04)
- C-11 analisis-atrasados-reportes (archivado 2026-06-04)
- C-12 comunicaciones-cola-worker (archivado 2026-06-04)
- C-13 encuentros-y-guardias (archivado 2026-06-04)
- C-14 evaluaciones-y-coloquios (archivado 2026-06-04)
- C-15 avisos-y-acknowledgment (archivado 2026-06-04)
- C-16 tareas-internas (archivado 2026-06-05)
- C-17 programas-y-fechas-academicas (archivado 2026-06-05)
- C-19 panel-auditoria-metricas (archivado 2026-06-05)
- C-20 perfil-y-mensajeria-interna (archivado 2026-06-05)
- C-21 frontend-shell-y-auth (archivado 2026-06-05)
- C-22 frontend-academico-docente (archivado 2026-06-05)
- C-23 frontend-coordinacion (archivado 2026-06-05)

### ❌ PENDIENTES (2/24)
- C-18 liquidaciones-y-honorarios (BACKEND pendiente - governance CRITICO)
- C-24 frontend-finanzas-y-admin (depende de C-18 + C-19)

## Stack del frontend real (C-21/22/23)
React 18 + TypeScript + Vite
Tailwind CSS
TanStack Query (server state)
React Hook Form + Zod (validación)
Axios + interceptor de auth + refresh transparente
Feature-based structure

## Implicaciones para el prototipo HTML

### 1. Lo que el prototipo hace bien ✅
- Roles correctos: ALUMNO, TUTOR, PROFESOR, COORDINADOR, ADMIN, FINANZAS (seed de C-04)
- RBAC por permiso modulo:accion reflejado en nav
- Flujos FL-01 (auth+2FA), FL-02 (profesor importar→analizar→comunicar), FL-04 (aprobación masiva),
  FL-07 (coloquio reserva), FL-09 (avisos+ack) — todos presentes
- Padrón destructivo con advertencia (RN-05) ✅
- Preview obligatorio (RN-16) ✅
- Aprobación de masivos (RN-17) ✅
- Avisos con ack (RN-19) ✅
- Liquidaciones con 3 universos (general/NEXO/factura, RN-35/36) ✅
- Cierre inmutable (RN-22) ✅

### 2. Gaps identificados vs CHANGES ⚠️
- Padrón: en el prototipo dice "versionado" pero C-09 dice VersionPadron sí existe
  (una activa por materia×cohorte, activar nueva desactiva anterior) — NO es destructivo total,
  es "la nueva versión reemplaza la activa". CORREGIR el copy del warning.
- Padrón: el prototipo no muestra la "vista previa" antes de activar (F1.3/F1.4) — solo el dropzone.
- Calificaciones: C-10 importa desde LMS con detección automática de columnas numéricas (RN-01)
  y textuales (RN-02). El prototipo refleja esto bien en el paso "preview de actividades".
- Comunicaciones: el destinatario debe estar cifrado en backend (modelo Comunicacion con
  destinatario [cifrado]) — transparente al front, ok.
- Encuentros: el prototipo no implementa el formulario de creación recurrente
  (día semana + cantidad semanas → genera N instancias, RN-13) — solo un toast.
- Tareas: C-16 tiene comentarios en hilo + workflow de estados. El prototipo solo lista tareas,
  no tiene el hilo de comentarios.
- Perfil: C-20 existe pero no hay vista de perfil en el prototipo.
- 2FA: el login muestra el aviso de 2FA pero no el flujo TOTP (C-03).
- Aviso GET /avisos/gestion (C-23 follow-up): endpoint nuevo para coordinador para listar TODOS
  los avisos del tenant — nuestro panel de gestión de avisos ya lo muestra, ✅ ok.
- C-18 PENDIENTE: el frontend de liquidaciones en el prototipo está diseñado pero el backend
  no existe aún. Al integrar, esperar C-18.
- C-24 PENDIENTE: el frontend real TypeScript para finanzas+admin está pendiente.
  Nuestro prototipo HTML es la guía visual para cuando lo implementen.

### 3. Cosas del real frontend TypeScript (C-21/22/23) que el prototipo debe alinear
- Tailwind classes — el prototipo usa clases custom (.aApp, .aSide, etc.). Al pasar al real,
  traducir a Tailwind.
- TanStack Query: los estados de carga/error/empty deben estar en el prototipo (hoy todo es data mock).
- React Hook Form + Zod: todos los forms del prototipo (asignación, comunicación, aviso, coloquio)
  necesitan validación explícita cuando pasen al real.
- El cliente HTTP real usa JWT refresh transparente — en el prototipo el login es simulado.

## Correcciones prioritarias en el prototipo
1. CORREGIR: copy de Padrón — no es "destruye todo", es "activa nueva versión (reemplaza activa)"
2. AGREGAR: preview de padrón antes de activar (F1.3)
3. AGREGAR: vista de Perfil propio (C-20 está implementado en backend)
4. AGREGAR: flujo 2FA en login (C-03 implementado)
5. AGREGAR: formulario real de encuentro recurrente (C-13 implementado)
6. AGREGAR: hilo de comentarios en Tareas (C-16 implementado)
7. PENDIENTE: C-18 backend → cuando esté, el prototipo de Liquidaciones ya está listo para conectar
