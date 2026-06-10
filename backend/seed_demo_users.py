"""Seed 5 usuarios demo en el tenant Demo. Idempotente.

Correr desde backend/:
    python seed_demo_users.py

Crea (o actualiza) los siguientes usuarios:
    coordinador@demo.com  /  Demo1234!  →  COORDINADOR  (Mariana Suárez)
    profesor@demo.com     /  Demo1234!  →  PROFESOR      (Sofía Ledesma)
    alumno@demo.com       /  Demo1234!  →  ALUMNO        (Joaquín Sosa)
    admin@demo.com        /  Admin1234! →  ADMIN         (Lucia Ferrer)
    tutor@demo.com        /  Demo1234!  →  TUTOR         (Carlos Méndez)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.security.passwords import hash_password, email_lookup_hash
from app.core.security.crypto import encrypt

TENANT_ID = '8531f634-3f1f-45da-9549-2f801d85c39b'

USERS = [
    {
        'email':    'coordinador@demo.com',
        'password': 'Demo1234!',
        'roles':    '["COORDINADOR"]',
        'nombre':   'Mariana',
        'apellidos':'Suárez',
    },
    {
        'email':    'profesor@demo.com',
        'password': 'Demo1234!',
        'roles':    '["PROFESOR"]',
        'nombre':   'Sofía',
        'apellidos':'Ledesma',
    },
    {
        'email':    'alumno@demo.com',
        'password': 'Demo1234!',
        'roles':    '["ALUMNO"]',
        'nombre':   'Joaquín',
        'apellidos':'Sosa',
    },
    {
        'email':    'admin@demo.com',
        'password': 'Admin1234!',
        'roles':    '["ADMIN"]',
        'nombre':   'Lucia',
        'apellidos':'Ferrer',
    },
    {
        'email':    'tutor@demo.com',
        'password': 'Demo1234!',
        'roles':    '["TUTOR"]',
        'nombre':   'Carlos',
        'apellidos':'Méndez',
    },
]


async def seed() -> None:
    from app.core.config import Settings
    engine = create_async_engine(Settings().DATABASE_URL)

    async with engine.begin() as conn:
        # 0) Tenant Demo — idempotente
        await conn.execute(text("""
            INSERT INTO tenants (id, nombre, estado, created_at, updated_at)
            VALUES (:tid, 'Demo', 'activo', now(), now())
            ON CONFLICT (id) DO NOTHING
        """), {'tid': TENANT_ID})
        print(f'OK  tenant Demo  id={TENANT_ID}')

        for u in USERS:
            email_enc  = encrypt(u['email'])
            email_hash = email_lookup_hash(u['email'])
            pwd_hash   = hash_password(u['password'])

            # 1) auth_identity — ON CONFLICT: actualizar password y roles
            await conn.execute(text("""
                INSERT INTO auth_identities
                    (id, tenant_id, email_encrypted, email_hash, password_hash, roles,
                     is_active, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :tid, :email_enc, :email_hash, :pwd_hash,
                     CAST(:roles AS jsonb), true, now(), now())
                ON CONFLICT ON CONSTRAINT uq_auth_identity_tenant_email
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    roles         = EXCLUDED.roles,
                    updated_at    = now()
            """), {
                'tid':        TENANT_ID,
                'email_enc':  email_enc,
                'email_hash': email_hash,
                'pwd_hash':   pwd_hash,
                'roles':      u['roles'],
            })

            # 2) recuperar el id de la auth_identity recién insertada/actualizada
            row = await conn.execute(text("""
                SELECT id FROM auth_identities
                WHERE tenant_id = :tid AND email_hash = :h AND deleted_at IS NULL
            """), {'tid': TENANT_ID, 'h': email_hash})
            identity_id = row.scalar()

            # 3) usuario (perfil de negocio) — check-then-insert (no unique en auth_identity_id)
            exists = await conn.execute(text("""
                SELECT id FROM usuario
                WHERE auth_identity_id = :auth_id AND deleted_at IS NULL
                LIMIT 1
            """), {'auth_id': str(identity_id)})
            if exists.fetchone() is None:
                u_email_enc = encrypt(u['email'])
                await conn.execute(text("""
                    INSERT INTO usuario
                        (id, tenant_id, email_encrypted, email_hash, nombre, apellidos,
                         estado, auth_identity_id, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :tid, :email_enc, :email_hash,
                         :nombre, :apellidos, 'activo', :auth_id, now(), now())
                """), {
                    'tid':        TENANT_ID,
                    'email_enc':  u_email_enc,
                    'email_hash': email_hash,
                    'nombre':     u['nombre'],
                    'apellidos':  u['apellidos'],
                    'auth_id':    str(identity_id),
                })
            else:
                await conn.execute(text("""
                    UPDATE usuario SET nombre = :nombre, apellidos = :apellidos, updated_at = now()
                    WHERE auth_identity_id = :auth_id AND deleted_at IS NULL
                """), {'nombre': u['nombre'], 'apellidos': u['apellidos'], 'auth_id': str(identity_id)})

            print(f'OK  {u["email"]:30s}  {u["roles"]:20s}  {u["nombre"]} {u["apellidos"]}')

    await engine.dispose()


asyncio.run(seed())
