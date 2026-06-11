-- reset_demo_data.sql — Reset de datos para grabar la demo.
--
-- Deja el entorno "demo-ready":
--   CONSERVA: tenant, RBAC (rol/permiso/rol_permiso), los 5 usuarios demo
--             (auth_identities + usuario), estructura académica
--             (carrera/materia/cohorte/programa_materia/fecha_academica),
--             asignaciones, y el padrón + calificaciones demo
--             (version_padron/entrada_padron/calificacion).
--   BORRA: el "junk" transaccional generado durante testing —
--             tareas, encuentros, coloquios/evaluaciones, mensajería,
--             avisos, comunicaciones, audit log y sesiones de login.
--
-- Idempotente: correrlo N veces deja el mismo estado.
-- Uso (contra la DB docker que usa la app):
--   docker exec -i active-trace-postgres-1 psql -U postgres -d activia_trace -v ON_ERROR_STOP=1 < backend/reset_demo_data.sql
--
-- NOTA: TRUNCATE ... CASCADE limpia también las tablas hijas
-- (instancia_encuentro, candidato/turno/reserva_evaluacion, hilo_participantes,
--  mensajes, acknowledgment_aviso, comentario_tarea, etc.). El CASCADE queda
-- contenido dentro del conjunto "junk" — ninguna tabla conservada referencia a estas.

BEGIN;

-- audit_event es append-only por diseño (puede tener triggers de inmutabilidad):
-- se desactivan solo para este reset del entorno demo local (NO afecta prod).
ALTER TABLE audit_event DISABLE TRIGGER ALL;

TRUNCATE TABLE
    tarea,            -- + comentario_tarea (CASCADE)
    slot_encuentro,   -- + instancia_encuentro (CASCADE)
    evaluacion,       -- + candidato_evaluacion, turno_evaluacion, reserva_evaluacion (CASCADE)
    hilos_mensaje,    -- + hilo_participantes, mensajes (CASCADE)
    aviso,            -- + acknowledgment_aviso (CASCADE)
    comunicacion,
    audit_event,
    refresh_sessions
RESTART IDENTITY CASCADE;

ALTER TABLE audit_event ENABLE TRIGGER ALL;

COMMIT;
