"""Seed RBAC completo para el tenant Demo. Idempotente."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TENANT_ID = '8531f634-3f1f-45da-9549-2f801d85c39b'

ROLES = ['ALUMNO', 'TUTOR', 'PROFESOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS']

PERMISOS = [
    ('academico:ver_propio',             'academico',      'ver_propio'),
    ('evaluacion:reservar',              'evaluacion',     'reservar'),
    ('avisos:confirmar',                 'avisos',         'confirmar'),
    ('calificaciones:importar',          'calificaciones', 'importar'),
    ('calificaciones:configurar-umbral', 'calificaciones', 'configurar-umbral'),
    ('atrasados:ver',                    'atrasados',      'ver'),
    ('entregas:ver_sin_corregir',        'entregas',       'ver_sin_corregir'),
    ('comunicacion:enviar',              'comunicacion',   'enviar'),
    ('comunicacion:aprobar',             'comunicacion',   'aprobar'),
    ('encuentros:gestionar',             'encuentros',     'gestionar'),
    ('guardias:registrar',               'guardias',       'registrar'),
    ('tareas:gestionar',                 'tareas',         'gestionar'),
    ('avisos:publicar',                  'avisos',         'publicar'),
    ('equipos:ver',                      'equipos',        'ver'),
    ('equipos:asignar',                  'equipos',        'asignar'),
    ('estructura:gestionar',             'estructura',     'gestionar'),
    ('usuarios:gestionar',               'usuarios',       'gestionar'),
    ('auditoria:ver',                    'auditoria',      'ver'),
    ('padron:cargar',                    'padron',         'cargar'),
    ('padron:gestionar',                 'padron',         'gestionar'),
    ('coloquios:gestionar',              'coloquios',      'gestionar'),
    ('coloquios:reservar',               'coloquios',      'reservar'),
    ('liquidaciones:operar_grilla',      'liquidaciones',  'operar_grilla'),
    ('liquidaciones:cerrar',             'liquidaciones',  'cerrar'),
    ('facturas:gestionar',               'facturas',       'gestionar'),
    ('tenant:configurar',                'tenant',         'configurar'),
    ('impersonacion:usar',               'impersonacion',  'usar'),
    ('inbox:usar',                       'inbox',          'usar'),
    ('perfil:editar',                    'perfil',         'editar'),
]

MATRIZ = [
    # ALUMNO
    ('ALUMNO', 'academico:ver_propio', 'global'),
    ('ALUMNO', 'evaluacion:reservar',  'global'),
    ('ALUMNO', 'avisos:confirmar',     'global'),
    ('ALUMNO', 'coloquios:reservar',   'global'),
    # TUTOR
    ('TUTOR', 'inbox:usar',               'global'),
    ('TUTOR', 'perfil:editar',            'propio'),
    ('TUTOR', 'avisos:confirmar',          'global'),
    ('TUTOR', 'atrasados:ver',             'global'),
    ('TUTOR', 'entregas:ver_sin_corregir', 'global'),
    ('TUTOR', 'encuentros:gestionar',      'global'),
    ('TUTOR', 'guardias:registrar',        'propio'),
    ('TUTOR', 'equipos:ver',               'propio'),
    ('TUTOR', 'padron:cargar',             'global'),
    ('TUTOR', 'tareas:gestionar',          'global'),
    # PROFESOR
    ('PROFESOR', 'inbox:usar',                   'global'),
    ('PROFESOR', 'perfil:editar',                'propio'),
    ('PROFESOR', 'avisos:confirmar',             'global'),
    ('PROFESOR', 'calificaciones:importar',      'propio'),
    ('PROFESOR', 'calificaciones:configurar-umbral', 'propio'),
    ('PROFESOR', 'atrasados:ver',                'propio'),
    ('PROFESOR', 'entregas:ver_sin_corregir',    'propio'),
    ('PROFESOR', 'comunicacion:enviar',          'propio'),
    ('PROFESOR', 'encuentros:gestionar',         'propio'),
    ('PROFESOR', 'guardias:registrar',           'propio'),
    ('PROFESOR', 'tareas:gestionar',             'propio'),
    ('PROFESOR', 'equipos:ver',                  'propio'),
    ('PROFESOR', 'padron:cargar',                'global'),
    ('PROFESOR', 'coloquios:gestionar',          'global'),
    # COORDINADOR
    ('COORDINADOR', 'inbox:usar',                   'global'),
    ('COORDINADOR', 'perfil:editar',                'propio'),
    ('COORDINADOR', 'avisos:confirmar',             'global'),
    ('COORDINADOR', 'calificaciones:importar',      'global'),
    ('COORDINADOR', 'calificaciones:configurar-umbral', 'global'),
    ('COORDINADOR', 'atrasados:ver',               'global'),
    ('COORDINADOR', 'entregas:ver_sin_corregir',   'global'),
    ('COORDINADOR', 'comunicacion:enviar',         'global'),
    ('COORDINADOR', 'comunicacion:aprobar',        'global'),
    ('COORDINADOR', 'encuentros:gestionar',        'global'),
    ('COORDINADOR', 'guardias:registrar',          'global'),
    ('COORDINADOR', 'tareas:gestionar',            'global'),
    ('COORDINADOR', 'avisos:publicar',             'global'),
    ('COORDINADOR', 'equipos:asignar',             'global'),
    ('COORDINADOR', 'equipos:ver',                 'global'),
    ('COORDINADOR', 'auditoria:ver',               'propio'),
    ('COORDINADOR', 'padron:cargar',               'global'),
    ('COORDINADOR', 'padron:gestionar',            'global'),
    ('COORDINADOR', 'coloquios:gestionar',         'global'),
    # NEXO
    ('NEXO', 'avisos:confirmar', 'global'),
    ('NEXO', 'equipos:ver',      'propio'),
    # ADMIN
    ('ADMIN', 'inbox:usar',                   'global'),
    ('ADMIN', 'perfil:editar',                'propio'),
    ('ADMIN', 'avisos:confirmar',             'global'),
    ('ADMIN', 'calificaciones:importar',      'global'),
    ('ADMIN', 'calificaciones:configurar-umbral', 'global'),
    ('ADMIN', 'atrasados:ver',                'global'),
    ('ADMIN', 'entregas:ver_sin_corregir',    'global'),
    ('ADMIN', 'comunicacion:enviar',          'global'),
    ('ADMIN', 'comunicacion:aprobar',         'global'),
    ('ADMIN', 'encuentros:gestionar',         'global'),
    ('ADMIN', 'guardias:registrar',           'global'),
    ('ADMIN', 'tareas:gestionar',             'global'),
    ('ADMIN', 'avisos:publicar',              'global'),
    ('ADMIN', 'equipos:asignar',              'global'),
    ('ADMIN', 'equipos:ver',                  'global'),
    ('ADMIN', 'estructura:gestionar',         'global'),
    ('ADMIN', 'usuarios:gestionar',           'global'),
    ('ADMIN', 'auditoria:ver',                'global'),
    ('ADMIN', 'tenant:configurar',            'global'),
    ('ADMIN', 'impersonacion:usar',           'global'),
    ('ADMIN', 'liquidaciones:operar_grilla',  'global'),
    ('ADMIN', 'liquidaciones:cerrar',         'global'),
    ('ADMIN', 'facturas:gestionar',           'global'),
    ('ADMIN', 'padron:cargar',                'global'),
    ('ADMIN', 'padron:gestionar',             'global'),
    ('ADMIN', 'coloquios:gestionar',          'global'),
    # FINANZAS
    ('FINANZAS', 'avisos:confirmar',            'global'),
    ('FINANZAS', 'auditoria:ver',               'global'),
    ('FINANZAS', 'liquidaciones:operar_grilla', 'global'),
    ('FINANZAS', 'liquidaciones:cerrar',        'global'),
    ('FINANZAS', 'facturas:gestionar',          'global'),
    ('FINANZAS', 'equipos:ver',                 'global'),
]

async def seed():
    from app.core.config import Settings
    engine = create_async_engine(Settings().DATABASE_URL)
    tid = TENANT_ID
    async with engine.begin() as conn:
        for nombre in ROLES:
            await conn.execute(text(
                'INSERT INTO rol (id, tenant_id, nombre, created_at, updated_at) '
                'VALUES (gen_random_uuid(), :tid, :nombre, now(), now()) '
                'ON CONFLICT ON CONSTRAINT uq_rol_tenant_nombre DO NOTHING'
            ), {'tid': tid, 'nombre': nombre})

        for codigo, modulo, accion in PERMISOS:
            await conn.execute(text(
                'INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at) '
                'VALUES (gen_random_uuid(), :tid, :codigo, :modulo, :accion, now(), now()) '
                'ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING'
            ), {'tid': tid, 'codigo': codigo, 'modulo': modulo, 'accion': accion})

        for rol_nombre, permiso_codigo, scope in MATRIZ:
            await conn.execute(text('''
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                SELECT gen_random_uuid(), :tid, r.id, p.id, CAST(:scope AS permiso_scope), now(), now()
                FROM rol r, permiso p
                WHERE r.tenant_id = :tid AND r.nombre = :rol
                  AND p.tenant_id = :tid AND p.codigo = :perm
                  AND r.deleted_at IS NULL AND p.deleted_at IS NULL
                ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
            '''), {'tid': tid, 'rol': rol_nombre, 'perm': permiso_codigo, 'scope': scope})

        r = await conn.execute(text('SELECT COUNT(*) FROM rol WHERE tenant_id = :tid'), {'tid': tid})
        print(f'Roles:    {r.scalar()}')
        r = await conn.execute(text('SELECT COUNT(*) FROM permiso WHERE tenant_id = :tid'), {'tid': tid})
        print(f'Permisos: {r.scalar()}')
        r = await conn.execute(text('SELECT COUNT(*) FROM rol_permiso WHERE tenant_id = :tid'), {'tid': tid})
        print(f'Grants:   {r.scalar()}')

    await engine.dispose()

asyncio.run(seed())
