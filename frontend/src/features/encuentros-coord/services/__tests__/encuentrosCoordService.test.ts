/**
 * Tests for encuentrosCoordService — stubs transport via axios-mock-adapter.
 * TDD: RED first, then GREEN.
 * Tasks 5.2, 5.3, 5.4.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarInstancias,
  listarGuardias,
  exportarGuardias,
} from '../encuentrosCoordService'
import type { InstanciaEncuentroRead, GuardiaRead, GuardiaParams } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})
afterEach(() => {
  mock.reset()
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const sampleInstancia: InstanciaEncuentroRead = {
  id: 'inst-uuid-1',
  slot_id: 'slot-uuid-1',
  materia_id: 'mat-uuid-1',
  fecha: '2024-04-10',
  hora: '18:00:00',
  titulo: 'Clase sincrónica 1',
  estado: 'Programado',
  meet_url: 'https://meet.google.com/abc',
  video_url: null,
  comentario: '',
}

const sampleGuardia: GuardiaRead = {
  id: 'guardia-uuid-1',
  asignacion_id: 'asig-uuid-1',
  materia_id: 'mat-uuid-1',
  carrera_id: 'car-uuid-1',
  cohorte_id: 'coh-uuid-1',
  dia: 'Lunes',
  horario: '10:00 - 12:00',
  estado: 'Pendiente',
  comentarios: '',
  creada_at: '2024-04-01T10:00:00',
}

// ---------------------------------------------------------------------------
// Task 5.2 — listarInstancias
// ---------------------------------------------------------------------------

describe('listarInstancias', () => {
  it('returns list of InstanciaEncuentroRead on 200', async () => {
    mock.onGet('/encuentros/instancias').reply(200, [sampleInstancia])
    const result = await listarInstancias({})
    expect(result).toEqual([sampleInstancia])
  })

  it('returns empty list on 200 with no rows', async () => {
    mock.onGet('/encuentros/instancias').reply(200, [])
    const result = await listarInstancias({})
    expect(result).toEqual([])
  })

  it('passes materia_id as query param when provided', async () => {
    mock.onGet('/encuentros/instancias').reply(200, [sampleInstancia])
    await listarInstancias({ materia_id: 'mat-uuid-1' })
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({ materia_id: 'mat-uuid-1' })
  })

  it('omits materia_id when null', async () => {
    mock.onGet('/encuentros/instancias').reply(200, [])
    await listarInstancias({ materia_id: null })
    const sentParams = mock.history.get[0].params ?? {}
    expect(sentParams).not.toHaveProperty('materia_id')
  })

  it('throws DomainError on 403 (missing permission)', async () => {
    mock.onGet('/encuentros/instancias').reply(403, { detail: 'Forbidden' })
    await expect(listarInstancias({})).rejects.toMatchObject({ status: 403 })
  })

  it('throws DomainError on 401 (unauthenticated)', async () => {
    mock.onGet('/encuentros/instancias').reply(401, { detail: 'Unauthorized' })
    await expect(listarInstancias({})).rejects.toMatchObject({ status: 401 })
  })
})

// ---------------------------------------------------------------------------
// Task 5.3 — listarGuardias
// ---------------------------------------------------------------------------

describe('listarGuardias', () => {
  it('returns list of GuardiaRead on 200', async () => {
    mock.onGet('/guardias').reply(200, [sampleGuardia])
    const result = await listarGuardias({})
    expect(result).toEqual([sampleGuardia])
  })

  it('returns empty list on 200 with no rows', async () => {
    mock.onGet('/guardias').reply(200, [])
    const result = await listarGuardias({})
    expect(result).toEqual([])
  })

  it('passes all filter params: materia_id, carrera_id, cohorte_id', async () => {
    mock.onGet('/guardias').reply(200, [sampleGuardia])
    const params: GuardiaParams = {
      materia_id: 'mat-1',
      carrera_id: 'car-1',
      cohorte_id: 'coh-1',
    }
    await listarGuardias(params)
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({
      materia_id: 'mat-1',
      carrera_id: 'car-1',
      cohorte_id: 'coh-1',
    })
  })

  it('passes dia and estado filters', async () => {
    mock.onGet('/guardias').reply(200, [])
    await listarGuardias({ dia: 'Lunes', estado: 'Pendiente' })
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({ dia: 'Lunes', estado: 'Pendiente' })
  })

  it('omits null filter values from request', async () => {
    mock.onGet('/guardias').reply(200, [])
    await listarGuardias({ materia_id: null, dia: null })
    const sentParams = mock.history.get[0].params ?? {}
    expect(sentParams).not.toHaveProperty('materia_id')
    expect(sentParams).not.toHaveProperty('dia')
  })

  it('throws DomainError on 403 (missing permission)', async () => {
    mock.onGet('/guardias').reply(403, { detail: 'Forbidden' })
    await expect(listarGuardias({})).rejects.toMatchObject({ status: 403 })
  })

  it('throws DomainError on 422 (invalid dia enum)', async () => {
    mock.onGet('/guardias').reply(422, { detail: 'Día inválido: badday' })
    await expect(listarGuardias({ dia: 'badday' })).rejects.toMatchObject({ status: 422 })
  })
})

// ---------------------------------------------------------------------------
// Task 5.4 — exportarGuardias (blob download)
// ---------------------------------------------------------------------------

describe('exportarGuardias', () => {
  it('returns a Blob on 200 from /guardias/export', async () => {
    const csvContent = 'id,dia\nguardia-1,Lunes\n'
    mock.onGet('/guardias/export').reply(200, new Blob([csvContent], { type: 'text/csv' }))
    const result = await exportarGuardias({})
    expect(result).toBeInstanceOf(Blob)
  })

  it('passes filter params to /guardias/export', async () => {
    mock.onGet('/guardias/export').reply(200, new Blob([''], { type: 'text/csv' }))
    await exportarGuardias({ materia_id: 'mat-1', dia: 'Lunes' })
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({ materia_id: 'mat-1', dia: 'Lunes' })
  })

  it('omits null filter values from export request', async () => {
    mock.onGet('/guardias/export').reply(200, new Blob([''], { type: 'text/csv' }))
    await exportarGuardias({ materia_id: null, carrera_id: null })
    const sentParams = mock.history.get[0].params ?? {}
    expect(sentParams).not.toHaveProperty('materia_id')
    expect(sentParams).not.toHaveProperty('carrera_id')
  })

  it('throws DomainError on 403 (missing permission for export)', async () => {
    mock.onGet('/guardias/export').reply(403, { detail: 'Forbidden' })
    await expect(exportarGuardias({})).rejects.toMatchObject({ status: 403 })
  })
})
