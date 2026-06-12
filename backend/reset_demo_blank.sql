-- reset_demo_blank.sql — Reset "default/en blanco" para grabar la demo desde cero.
--
-- Deja SOLO: tenant, RBAC (rol/permiso/rol_permiso) y los 5 usuarios demo
-- (auth_identities + usuario). TODO lo demás queda vacío para construirlo en vivo
-- durante el video (estructura académica vía /admin/estructura, asignaciones,
-- importación de padrón/calificaciones, etc.).
--
-- BORRA: estructura (carrera/materia/cohorte/programa/fecha), asignaciones, padrón,
--        calificaciones, umbral, y todo el transaccional (tareas/encuentros/coloquios/
--        mensajería/avisos/comunicaciones/audit/sesiones).
--
-- Prerrequisito para que la app siga andando: NINGÚN cambio de schema, solo data.
-- Requiere /admin/estructura (C-29) para recrear materias/carreras desde la UI.
--
-- Idempotente. Uso (contra la DB docker que usa la app):
--   docker exec -i active-trace-postgres-1 psql -U postgres -d activia_trace -v ON_ERROR_STOP=1 < backend/reset_demo_blank.sql
--
-- Alternativa con datos pre-cargados: backend/reset_demo_data.sql (conserva estructura
-- + padrón + calificaciones). Para repoblar estructura base: python seed_demo_estructura.py.

BEGIN;

-- audit_event es append-only (triggers de inmutabilidad): se desactivan solo para
-- este reset del entorno demo local (NO afecta prod).
ALTER TABLE audit_event DISABLE TRIGGER ALL;

TRUNCATE TABLE
    -- estructura académica
    carrera, materia, cohorte, programa_materia, fecha_academica,
    -- asignaciones
    asignacion,
    -- padrón + calificaciones
    version_padron, entrada_padron, calificacion, umbral_materia,
    -- transaccional (junk de testing)
    tarea, slot_encuentro, evaluacion, hilos_mensaje, aviso, comunicacion,
    audit_event, refresh_sessions
RESTART IDENTITY CASCADE;

ALTER TABLE audit_event ENABLE TRIGGER ALL;

COMMIT;
