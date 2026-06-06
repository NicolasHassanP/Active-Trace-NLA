"""Seed usuario admin@demo.com en el tenant Demo. Idempotente.

Correr desde backend/:
    python seed_demo_user.py

Requiere que .env esté presente y que las migraciones estén aplicadas.
Correr DESPUÉS de seed_rbac_demo.py.
"""
import asyncio
import os
import sys

# Asegurar que los módulos de app sean resolvibles cuando se corre desde backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import Settings
from app.core.security.passwords import hash_password, email_lookup_hash
from app.core.security.crypto import encrypt

TENANT_ID = '8531f634-3f1f-45da-9549-2f801d85c39b'
EMAIL = 'admin@demo.com'
PASSWORD = 'Admin1234!'


async def seed() -> None:
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL)

    email_enc = encrypt(EMAIL)
    email_hash = email_lookup_hash(EMAIL)
    pwd_hash = hash_password(PASSWORD)

    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO auth_identities
                (id, tenant_id, email_encrypted, email_hash, password_hash, roles, is_active,
                 created_at, updated_at)
            VALUES
                (gen_random_uuid(), :tid, :email_enc, :email_hash, :pwd_hash,
                 '["ADMIN"]'::jsonb, true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_auth_identity_tenant_email DO NOTHING
        """), {
            'tid': TENANT_ID,
            'email_enc': email_enc,
            'email_hash': email_hash,
            'pwd_hash': pwd_hash,
        })

        row = await conn.execute(text(
            'SELECT id, is_active FROM auth_identities '
            'WHERE tenant_id = :tid AND email_hash = :h AND deleted_at IS NULL'
        ), {'tid': TENANT_ID, 'h': email_hash})
        result = row.fetchone()

    await engine.dispose()

    if result:
        print(f'OK  {EMAIL}  id={result[0]}  activo={result[1]}')
    else:
        print(f'SKIP {EMAIL} — ya existía (ON CONFLICT)')


asyncio.run(seed())
