/**
 * Tests for estructuraAdminService — stubs transport (axios-mock-adapter).
 * Covers GET/POST/PATCH/DELETE for carreras, materias, cohortes.
 * Contracts:
 *   - tenant_id NEVER in request body
 *   - 409 → DomainError { status: 409 }
 *   - 404 → DomainError { status: 404 }
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarCarreras,
  crearCarrera,
  editarCarrera,
  darBajaCarrera,
  listarMaterias,
  crearMateria,
  editarMateria,
  darBajaMateria,
  listarCohortes,
  crearCohorte,
  editarCohorte,
  darBajaCohorte,
} from '../estructuraAdminService'
import type {
  CarreraRead,
  CarreraCreate,
  MateriaRead,
  MateriaCreate,
  CohorteRead,
  CohorteCreate,
} from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

afterEach(() => {
  mock.reset()
})

// ── Fixtures ────────────────────────────────────────────────────────────────

const sampleCarrera: CarreraRead = {
  id: 'car-uuid-1',
  codigo: 'ING-SIS',
  nombre: 'Ingeniería en Sistemas',
  estado: 'activa',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

const sampleMateria: MateriaRead = {
  id: 'mat-uuid-1',
  codigo: 'MAT101',
  nombre: 'Matemática I',
  estado: 'activa',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

const sampleCohorte: CohorteRead = {
  id: 'coh-uuid-1',
  carrera_id: 'car-uuid-1',
  nombre: '2026',
  anio: 2026,
  vig_desde: '2026-03-01',
  vig_hasta: null,
  estado: 'activa',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

// ── listarCarreras ──────────────────────────────────────────────────────────

describe('listarCarreras', () => {
  it('returns CarreraRead[] on 200', async () => {
    mock.onGet('/admin/carreras').reply(200, [sampleCarrera])
    const result = await listarCarreras()
    expect(result).toEqual([sampleCarrera])
  })

  it('returns empty array on 200 with no items', async () => {
    mock.onGet('/admin/carreras').reply(200, [])
    const result = await listarCarreras()
    expect(result).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/admin/carreras').reply(403, { detail: 'sin permiso estructura:ver' })
    await expect(listarCarreras()).rejects.toMatchObject({ status: 403 })
  })
})

// ── crearCarrera ────────────────────────────────────────────────────────────

describe('crearCarrera', () => {
  const body: CarreraCreate = { codigo: 'ING-SIS', nombre: 'Ingeniería en Sistemas' }

  it('returns CarreraRead on 201', async () => {
    mock.onPost('/admin/carreras').reply(201, sampleCarrera)
    const result = await crearCarrera(body)
    expect(result).toEqual(sampleCarrera)
  })

  it('sends codigo and nombre; never tenant_id', async () => {
    mock.onPost('/admin/carreras').reply(201, sampleCarrera)
    await crearCarrera(body)
    const sent = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sent).toMatchObject(body)
    expect(sent).not.toHaveProperty('tenant_id')
  })

  it('throws DomainError on 409 (unicidad)', async () => {
    mock.onPost('/admin/carreras').reply(409, { detail: 'Código duplicado' })
    await expect(crearCarrera(body)).rejects.toMatchObject({ status: 409 })
  })

  it('throws DomainError on 403', async () => {
    mock.onPost('/admin/carreras').reply(403, { detail: 'sin permiso' })
    await expect(crearCarrera(body)).rejects.toMatchObject({ status: 403 })
  })
})

// ── editarCarrera ───────────────────────────────────────────────────────────

describe('editarCarrera', () => {
  it('returns updated CarreraRead on 200', async () => {
    const updated = { ...sampleCarrera, nombre: 'Ingeniería en Sistemas de Info' }
    mock.onPatch('/admin/carreras/car-uuid-1').reply(200, updated)
    const result = await editarCarrera('car-uuid-1', { nombre: 'Ingeniería en Sistemas de Info' })
    expect(result.nombre).toBe('Ingeniería en Sistemas de Info')
  })

  it('throws DomainError on 409 (cohortes abiertas)', async () => {
    mock.onPatch('/admin/carreras/car-uuid-1').reply(409, { detail: 'Carrera con cohortes abiertas' })
    await expect(editarCarrera('car-uuid-1', { estado: 'inactiva' })).rejects.toMatchObject({ status: 409 })
  })

  it('throws DomainError on 404', async () => {
    mock.onPatch('/admin/carreras/no-existe').reply(404, { detail: 'Carrera no encontrada' })
    await expect(editarCarrera('no-existe', { nombre: 'X' })).rejects.toMatchObject({ status: 404 })
  })
})

// ── darBajaCarrera ──────────────────────────────────────────────────────────

describe('darBajaCarrera', () => {
  it('resolves undefined on 204', async () => {
    mock.onDelete('/admin/carreras/car-uuid-1').reply(204)
    const result = await darBajaCarrera('car-uuid-1')
    expect(result).toBeUndefined()
  })

  it('throws DomainError on 404', async () => {
    mock.onDelete('/admin/carreras/no-existe').reply(404, { detail: 'Carrera no encontrada' })
    await expect(darBajaCarrera('no-existe')).rejects.toMatchObject({ status: 404 })
  })
})

// ── listarMaterias ──────────────────────────────────────────────────────────

describe('listarMaterias', () => {
  it('returns MateriaRead[] on 200', async () => {
    mock.onGet('/admin/materias').reply(200, [sampleMateria])
    const result = await listarMaterias()
    expect(result).toEqual([sampleMateria])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/admin/materias').reply(403, { detail: 'sin permiso' })
    await expect(listarMaterias()).rejects.toMatchObject({ status: 403 })
  })
})

// ── crearMateria ────────────────────────────────────────────────────────────

describe('crearMateria', () => {
  const body: MateriaCreate = { codigo: 'MAT101', nombre: 'Matemática I' }

  it('returns MateriaRead on 201', async () => {
    mock.onPost('/admin/materias').reply(201, sampleMateria)
    const result = await crearMateria(body)
    expect(result).toEqual(sampleMateria)
  })

  it('never sends tenant_id', async () => {
    mock.onPost('/admin/materias').reply(201, sampleMateria)
    await crearMateria(body)
    const sent = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sent).not.toHaveProperty('tenant_id')
  })

  it('throws DomainError on 409', async () => {
    mock.onPost('/admin/materias').reply(409, { detail: 'Código duplicado' })
    await expect(crearMateria(body)).rejects.toMatchObject({ status: 409 })
  })
})

// ── editarMateria ───────────────────────────────────────────────────────────

describe('editarMateria', () => {
  it('returns updated MateriaRead on 200', async () => {
    const updated = { ...sampleMateria, nombre: 'Matemática II' }
    mock.onPatch('/admin/materias/mat-uuid-1').reply(200, updated)
    const result = await editarMateria('mat-uuid-1', { nombre: 'Matemática II' })
    expect(result.nombre).toBe('Matemática II')
  })

  it('throws DomainError on 404', async () => {
    mock.onPatch('/admin/materias/no-existe').reply(404, { detail: 'Materia no encontrada' })
    await expect(editarMateria('no-existe', { nombre: 'X' })).rejects.toMatchObject({ status: 404 })
  })
})

// ── darBajaMateria ──────────────────────────────────────────────────────────

describe('darBajaMateria', () => {
  it('resolves undefined on 204', async () => {
    mock.onDelete('/admin/materias/mat-uuid-1').reply(204)
    await expect(darBajaMateria('mat-uuid-1')).resolves.toBeUndefined()
  })
})

// ── listarCohortes ──────────────────────────────────────────────────────────

describe('listarCohortes', () => {
  it('returns CohorteRead[] on 200', async () => {
    mock.onGet('/admin/cohortes').reply(200, [sampleCohorte])
    const result = await listarCohortes()
    expect(result).toEqual([sampleCohorte])
  })

  it('forwards optional carrera_id filter', async () => {
    mock.onGet('/admin/cohortes').reply(200, [sampleCohorte])
    await listarCohortes('car-uuid-1')
    const params = mock.history.get[0].params as Record<string, string> | undefined
    expect(params).toEqual({ carrera_id: 'car-uuid-1' })
  })

  it('sends no params when carrera_id is omitted', async () => {
    mock.onGet('/admin/cohortes').reply(200, [sampleCohorte])
    await listarCohortes()
    const params = mock.history.get[0].params as Record<string, string> | undefined
    expect(params).toBeUndefined()
  })
})

// ── crearCohorte ────────────────────────────────────────────────────────────

describe('crearCohorte', () => {
  const body: CohorteCreate = {
    carrera_id: 'car-uuid-1',
    nombre: '2026',
    anio: 2026,
    vig_desde: '2026-03-01',
  }

  it('returns CohorteRead on 201', async () => {
    mock.onPost('/admin/cohortes').reply(201, sampleCohorte)
    const result = await crearCohorte(body)
    expect(result).toEqual(sampleCohorte)
  })

  it('sends carrera_id and never tenant_id', async () => {
    mock.onPost('/admin/cohortes').reply(201, sampleCohorte)
    await crearCohorte(body)
    const sent = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sent).toHaveProperty('carrera_id', 'car-uuid-1')
    expect(sent).not.toHaveProperty('tenant_id')
  })

  it('allows vig_hasta null (cohorte abierta)', async () => {
    mock.onPost('/admin/cohortes').reply(201, sampleCohorte)
    await crearCohorte({ ...body, vig_hasta: null })
    const sent = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sent.vig_hasta).toBeNull()
  })

  it('throws DomainError on 409 (carrera inactiva)', async () => {
    mock.onPost('/admin/cohortes').reply(409, { detail: 'Carrera inactiva' })
    await expect(crearCohorte(body)).rejects.toMatchObject({ status: 409 })
  })

  it('throws DomainError on 404 (carrera no encontrada)', async () => {
    mock.onPost('/admin/cohortes').reply(404, { detail: 'Carrera no encontrada' })
    await expect(crearCohorte(body)).rejects.toMatchObject({ status: 404 })
  })
})

// ── editarCohorte ───────────────────────────────────────────────────────────

describe('editarCohorte', () => {
  it('returns updated CohorteRead on 200', async () => {
    const updated = { ...sampleCohorte, nombre: '2026-B' }
    mock.onPatch('/admin/cohortes/coh-uuid-1').reply(200, updated)
    const result = await editarCohorte('coh-uuid-1', { nombre: '2026-B' })
    expect(result.nombre).toBe('2026-B')
  })

  it('throws DomainError on 409 (carrera inactiva)', async () => {
    mock.onPatch('/admin/cohortes/coh-uuid-1').reply(409, { detail: 'Carrera inactiva' })
    await expect(editarCohorte('coh-uuid-1', { estado: 'activa' })).rejects.toMatchObject({ status: 409 })
  })
})

// ── darBajaCohorte ──────────────────────────────────────────────────────────

describe('darBajaCohorte', () => {
  it('resolves undefined on 204', async () => {
    mock.onDelete('/admin/cohortes/coh-uuid-1').reply(204)
    await expect(darBajaCohorte('coh-uuid-1')).resolves.toBeUndefined()
  })
})
