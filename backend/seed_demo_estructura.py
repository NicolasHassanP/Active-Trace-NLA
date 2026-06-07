"""Seed de estructura académica demo. Idempotente.

Crea en el tenant Demo:
  - 1 Carrera:  Tecnicatura en Desarrollo de Software (TDS)
  - 2 Materias: Análisis Matemático I (MAT01) · Programación I (PRG01)
  - 1 Cohorte:  2026-1C  (vigente desde 2026-03-01, sin fecha de cierre)
  - 2 Asignaciones:
      · Sofía Ledesma (profesor@demo.com) → PROFESOR · MAT01 · TDS · 2026-1C · comisión 1A
      · Mariana Suárez (coordinador@demo.com) → COORDINADOR · MAT01 · TDS · 2026-1C

IDs fijos (para poder referenciarlos en la UI sin buscarlos):
  CARRERA_ID  = f1000001-f100-f100-f100-f10000000001
  MATERIA_ID  = f2000002-f200-f200-f200-f20000000002   ← usar en /padron y /calificaciones
  COHORTE_ID  = f3000003-f300-f300-f300-f30000000003   ← usar en /padron y /calificaciones
  MATERIA2_ID = f4000004-f400-f400-f400-f40000000004   (Programación I — sin asignación)

Correr:
  docker cp backend/seed_demo_estructura.py active-trace-nla-api-1:/app/
  docker exec active-trace-nla-api-1 python seed_demo_estructura.py

Prerequisito: seed_demo_users.py ya debe haber corrido (necesita los usuarios).
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.security.passwords import email_lookup_hash

TENANT_ID   = '8531f634-3f1f-45da-9549-2f801d85c39b'
CARRERA_ID  = 'f1000001-f100-f100-f100-f10000000001'
MATERIA_ID  = 'f2000002-f200-f200-f200-f20000000002'
MATERIA2_ID = 'f4000004-f400-f400-f400-f40000000004'
COHORTE_ID  = 'f3000003-f300-f300-f300-f30000000003'


async def seed() -> None:
    from app.core.config import Settings
    engine = create_async_engine(Settings().DATABASE_URL)

    async with engine.begin() as conn:

        # ── 1. Carrera ──────────────────────────────────────────────────────
        exists = await conn.execute(text(
            "SELECT id FROM carrera WHERE id = :id AND deleted_at IS NULL"
        ), {'id': CARRERA_ID})
        if exists.fetchone() is None:
            await conn.execute(text("""
                INSERT INTO carrera (id, tenant_id, codigo, nombre, estado, created_at, updated_at)
                VALUES (:id, :tid, 'TDS', 'Tecnicatura en Desarrollo de Software',
                        'activa', now(), now())
            """), {'id': CARRERA_ID, 'tid': TENANT_ID})
            print(f'OK  carrera   TDS  id={CARRERA_ID}')
        else:
            print(f'--  carrera   TDS  ya existe')

        # ── 2. Materias ─────────────────────────────────────────────────────
        for mid, codigo, nombre in [
            (MATERIA_ID,  'MAT01', 'Análisis Matemático I'),
            (MATERIA2_ID, 'PRG01', 'Programación I'),
        ]:
            exists = await conn.execute(text(
                "SELECT id FROM materia WHERE id = :id AND deleted_at IS NULL"
            ), {'id': mid})
            if exists.fetchone() is None:
                await conn.execute(text("""
                    INSERT INTO materia (id, tenant_id, codigo, nombre, estado, created_at, updated_at)
                    VALUES (:id, :tid, :codigo, :nombre, 'activa', now(), now())
                """), {'id': mid, 'tid': TENANT_ID, 'codigo': codigo, 'nombre': nombre})
                print(f'OK  materia   {codigo}  id={mid}')
            else:
                print(f'--  materia   {codigo}  ya existe')

        # ── 3. Cohorte ──────────────────────────────────────────────────────
        exists = await conn.execute(text(
            "SELECT id FROM cohorte WHERE id = :id AND deleted_at IS NULL"
        ), {'id': COHORTE_ID})
        if exists.fetchone() is None:
            await conn.execute(text("""
                INSERT INTO cohorte
                    (id, tenant_id, carrera_id, nombre, anio, vig_desde, vig_hasta,
                     estado, created_at, updated_at)
                VALUES (:id, :tid, :cid, '2026-1C', 2026, '2026-03-01', NULL,
                        'activa', now(), now())
            """), {'id': COHORTE_ID, 'tid': TENANT_ID, 'cid': CARRERA_ID})
            print(f'OK  cohorte   2026-1C  id={COHORTE_ID}')
        else:
            print(f'--  cohorte   2026-1C  ya existe')

        # ── 4. Asignaciones ─────────────────────────────────────────────────
        asignaciones = [
            {
                'email':      'profesor@demo.com',
                'rol':        'PROFESOR',
                'materia_id': MATERIA_ID,
                'carrera_id': CARRERA_ID,
                'cohorte_id': COHORTE_ID,
                'comisiones': '["1A"]',
                'desde':      '2026-03-01',
            },
            {
                'email':      'coordinador@demo.com',
                'rol':        'COORDINADOR',
                'materia_id': MATERIA_ID,
                'carrera_id': CARRERA_ID,
                'cohorte_id': COHORTE_ID,
                'comisiones': '[]',
                'desde':      '2026-03-01',
            },
        ]

        for a in asignaciones:
            h = email_lookup_hash(a['email'])

            # Obtener usuario_id
            row = await conn.execute(text("""
                SELECT id FROM usuario
                WHERE tenant_id = :tid AND email_hash = :h AND deleted_at IS NULL
                LIMIT 1
            """), {'tid': TENANT_ID, 'h': h})
            usuario_id = row.scalar()
            if usuario_id is None:
                print(f'!!  usuario {a["email"]} no encontrado — corré seed_demo_users.py primero')
                continue

            # Verificar si ya existe la asignación (mismo usuario+rol+materia+cohorte vigente)
            exists = await conn.execute(text("""
                SELECT id FROM asignacion
                WHERE tenant_id    = :tid
                  AND usuario_id   = :uid
                  AND rol          = :rol
                  AND materia_id   = :mid
                  AND cohorte_id   = :cid
                  AND deleted_at IS NULL
                LIMIT 1
            """), {
                'tid': TENANT_ID,
                'uid': str(usuario_id),
                'rol': a['rol'],
                'mid': a['materia_id'],
                'cid': a['cohorte_id'],
            })
            if exists.fetchone() is None:
                await conn.execute(text("""
                    INSERT INTO asignacion
                        (id, tenant_id, usuario_id, rol, materia_id, carrera_id, cohorte_id,
                         comisiones, desde, hasta, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :tid, :uid, :rol, :mid, :cid2, :cid,
                         CAST(:comisiones AS jsonb), :desde, NULL, now(), now())
                """), {
                    'tid':        TENANT_ID,
                    'uid':        str(usuario_id),
                    'rol':        a['rol'],
                    'mid':        a['materia_id'],
                    'cid2':       a['carrera_id'],
                    'cid':        a['cohorte_id'],
                    'comisiones': a['comisiones'],
                    'desde':      a['desde'],
                })
                print(f'OK  asignacion  {a["email"]:30s}  {a["rol"]:12s}  MAT01 · 2026-1C')
            else:
                print(f'--  asignacion  {a["email"]:30s}  {a["rol"]:12s}  ya existe')

    await engine.dispose()
    print()
    print('IDs para usar en la UI:')
    print(f'  Materia  (Análisis Matemático I):  {MATERIA_ID}')
    print(f'  Cohorte  (2026-1C):                {COHORTE_ID}')
    print()
    print('Flujo de testing:')
    print('  1. /padron         → subir backend/fixtures/padron_demo.csv')
    print('     Seleccionar materia MAT01 · cohorte 2026-1C')
    print('  2. /calificaciones → subir backend/fixtures/calificaciones_demo.csv')
    print('     Seleccionar las 3 actividades detectadas · umbral 60%')
    print('  3. /atrasados      → ver Pedro Ramírez, Martín Silva, Diego Fernández, Juan Herrera')


asyncio.run(seed())
