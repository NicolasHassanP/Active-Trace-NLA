/**
 * Tests for auditoriaService — stubs transport (axios-mock-adapter).
 * Covers GET /auditoria (list), 4 metric endpoints, ultimas-acciones.
 * Read-only service: no mutations.
 * Contracts: never sends body; tenant_id never in request.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarEventos,
  getAccionesPorDia,
  getInteraccionesDocente,
  getInteraccionesDocenteMateria,
  getComunicacionesPorDocente,
  getUltimasAcciones,
} from '../auditoriaService'
import type {
  AuditEventRead,
  AccionesPorDiaResponse,
  InteraccionesDocenteResponse,
  InteraccionesDocenteMateriaResponse,
  ComunicacionesPorDocenteResponse,
  UltimaAccionItem,
} from '../../types'

let mock: MockAdapter

beforeEach(() => { mock = new MockAdapter(apiClient) })
afterEach(() => { mock.reset() })

// ── Fixtures ────────────────────────────────────────────────────────────────

const sampleEvent: AuditEventRead = {
  id: 'evt-uuid-1',
  tenant_id: 'ten-uuid-1',
  actor_user_id: 'usr-uuid-1',
  impersonated_user_id: null,
  accion: 'LOGIN',
  modulo: 'auth',
  entidad_tipo: 'Usuario',
  entidad_id: null,
  resultado: 'ok',
  registros_afectados: null,
  ip: '127.0.0.1',
  user_agent: 'TestAgent',
  before: null,
  after: null,
  created_at: '2026-06-01T10:00:00',
}

// ── listarEventos ──────────────────────────────────────────────────────────

describe('listarEventos', () => {
  it('returns AuditEventRead[] on 200', async () => {
    mock.onGet('/auditoria').reply(200, [sampleEvent])
    const result = await listarEventos({})
    expect(result).toEqual([sampleEvent])
  })

  it('sends limit and offset query params', async () => {
    mock.onGet('/auditoria').reply(200, [])
    await listarEventos({ limit: 20, offset: 40 })
    const params = mock.history.get[0].params as Record<string, unknown>
    expect(params.limit).toBe(20)
    expect(params.offset).toBe(40)
  })

  it('sends desde/hasta filter params when provided', async () => {
    mock.onGet('/auditoria').reply(200, [])
    await listarEventos({ desde: '2026-01-01', hasta: '2026-06-30' })
    const params = mock.history.get[0].params as Record<string, string>
    expect(params.desde).toBe('2026-01-01')
    expect(params.hasta).toBe('2026-06-30')
  })

  it('omits undefined params (no tenant_id ever)', async () => {
    mock.onGet('/auditoria').reply(200, [])
    await listarEventos({})
    const params = mock.history.get[0].params as Record<string, unknown> | undefined
    // When no filters provided, params should be undefined (nothing sent)
    // or if an object, must never include tenant_id or desde
    if (params != null) {
      expect(params).not.toHaveProperty('tenant_id')
      expect(params).not.toHaveProperty('desde')
    } else {
      expect(params).toBeUndefined()
    }
  })

  it('returns empty array on 200 with empty list', async () => {
    mock.onGet('/auditoria').reply(200, [])
    expect(await listarEventos({})).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/auditoria').reply(403, { detail: 'sin permiso auditoria:ver' })
    await expect(listarEventos({})).rejects.toMatchObject({ status: 403 })
  })
})

// ── getAccionesPorDia ──────────────────────────────────────────────────────

describe('getAccionesPorDia', () => {
  const response: AccionesPorDiaResponse = {
    items: [{ dia: '2026-06-01T00:00:00', total: 5 }],
  }

  it('returns AccionesPorDiaResponse on 200', async () => {
    mock.onGet('/auditoria/metricas/acciones-por-dia').reply(200, response)
    const result = await getAccionesPorDia({})
    expect(result.items).toHaveLength(1)
  })

  it('sends desde/hasta when provided', async () => {
    mock.onGet('/auditoria/metricas/acciones-por-dia').reply(200, response)
    await getAccionesPorDia({ desde: '2026-01-01', hasta: '2026-06-30' })
    const params = mock.history.get[0].params as Record<string, string>
    expect(params.desde).toBe('2026-01-01')
    expect(params.hasta).toBe('2026-06-30')
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/auditoria/metricas/acciones-por-dia').reply(403, { detail: 'sin permiso' })
    await expect(getAccionesPorDia({})).rejects.toMatchObject({ status: 403 })
  })
})

// ── getInteraccionesDocente ────────────────────────────────────────────────

describe('getInteraccionesDocente', () => {
  const response: InteraccionesDocenteResponse = {
    items: [{ actor_user_id: 'usr-1', accion: 'LOGIN', total: 3 }],
  }

  it('returns InteraccionesDocenteResponse on 200', async () => {
    mock.onGet('/auditoria/metricas/interacciones-docente').reply(200, response)
    const result = await getInteraccionesDocente({})
    expect(result.items).toHaveLength(1)
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/auditoria/metricas/interacciones-docente').reply(403, { detail: 'sin permiso' })
    await expect(getInteraccionesDocente({})).rejects.toMatchObject({ status: 403 })
  })
})

// ── getInteraccionesDocenteMateria ─────────────────────────────────────────

describe('getInteraccionesDocenteMateria', () => {
  const response: InteraccionesDocenteMateriaResponse = {
    items: [{ actor_user_id: 'usr-1', materia_id: 'mat-1', total: 2 }],
  }

  it('returns InteraccionesDocenteMateriaResponse on 200', async () => {
    mock.onGet('/auditoria/metricas/interacciones-docente-materia').reply(200, response)
    const result = await getInteraccionesDocenteMateria({})
    expect(result.items).toHaveLength(1)
  })
})

// ── getComunicacionesPorDocente ────────────────────────────────────────────

describe('getComunicacionesPorDocente', () => {
  const response: ComunicacionesPorDocenteResponse = {
    items: [{ enviado_por: 'usr-1', estado: 'ENVIADA', total: 10 }],
  }

  it('returns ComunicacionesPorDocenteResponse on 200', async () => {
    mock.onGet('/auditoria/metricas/comunicaciones-por-docente').reply(200, response)
    const result = await getComunicacionesPorDocente()
    expect(result.items).toHaveLength(1)
  })
})

// ── getUltimasAcciones ─────────────────────────────────────────────────────

describe('getUltimasAcciones', () => {
  const sampleUltima: UltimaAccionItem = sampleEvent

  it('returns UltimaAccionItem[] on 200', async () => {
    mock.onGet('/auditoria/ultimas-acciones').reply(200, [sampleUltima])
    const result = await getUltimasAcciones()
    expect(result).toEqual([sampleUltima])
  })

  it('sends limite param when provided', async () => {
    mock.onGet('/auditoria/ultimas-acciones').reply(200, [])
    await getUltimasAcciones({ limite: 10 })
    const params = mock.history.get[0].params as Record<string, unknown>
    expect(params.limite).toBe(10)
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/auditoria/ultimas-acciones').reply(403, { detail: 'sin permiso' })
    await expect(getUltimasAcciones()).rejects.toMatchObject({ status: 403 })
  })
})
