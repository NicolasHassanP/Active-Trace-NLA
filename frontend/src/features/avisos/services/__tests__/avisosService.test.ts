/**
 * Tests for avisosService — stubs transport via axios-mock-adapter.
 * Tasks 2.2, 2.3, 2.4, 2.5 (Zod schema).
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  crearAviso,
  actualizarAviso,
  eliminarAviso,
  listarGestion,
  listarFeed,
  listarPendientes,
  ackAviso,
} from '../avisosService'
import { avisoFormSchema } from '../avisosService'
import type { AvisoRead, CrearAvisoRequest } from '../../types'

let mock: MockAdapter
beforeEach(() => { mock = new MockAdapter(apiClient) })
afterEach(() => { mock.reset() })

const sampleAviso: AvisoRead = {
  id: 'av-1',
  tenant_id: 'ten-1',
  alcance: 'Global',
  materia_id: null,
  cohorte_id: null,
  rol_destino: null,
  severidad: 'Info',
  titulo: 'Test',
  cuerpo: 'Cuerpo',
  inicio_en: '2024-03-01T00:00:00',
  fin_en: '2024-04-01T00:00:00',
  orden: 100,
  activo: true,
  requiere_ack: false,
  ack_count: 0,
}

// ---------------------------------------------------------------------------
// Task 2.2 — gestión
// ---------------------------------------------------------------------------
describe('crearAviso', () => {
  const body: CrearAvisoRequest = {
    alcance: 'Global',
    titulo: 'Test',
    cuerpo: 'Cuerpo',
    inicio_en: '2024-03-01T00:00:00',
    fin_en: '2024-04-01T00:00:00',
  }

  it('returns AvisoRead on 201', async () => {
    mock.onPost('/avisos').reply(201, sampleAviso)
    const result = await crearAviso(body)
    expect(result).toEqual(sampleAviso)
  })

  it('throws DomainError on 403', async () => {
    mock.onPost('/avisos').reply(403, { detail: 'Forbidden' })
    await expect(crearAviso(body)).rejects.toMatchObject({ status: 403 })
  })
})

describe('actualizarAviso', () => {
  it('returns updated AvisoRead on 200', async () => {
    mock.onPut('/avisos/av-1').reply(200, { ...sampleAviso, titulo: 'Actualizado' })
    const result = await actualizarAviso('av-1', { titulo: 'Actualizado' })
    expect(result.titulo).toBe('Actualizado')
  })

  it('throws DomainError on 404', async () => {
    mock.onPut('/avisos/no-existe').reply(404, { detail: 'Aviso no encontrado' })
    await expect(actualizarAviso('no-existe', { titulo: 'X' })).rejects.toMatchObject({ status: 404 })
  })
})

describe('eliminarAviso', () => {
  it('resolves on 204', async () => {
    mock.onDelete('/avisos/av-1').reply(204)
    await expect(eliminarAviso('av-1')).resolves.toBeUndefined()
  })

  it('throws DomainError on 404', async () => {
    mock.onDelete('/avisos/no-existe').reply(404, { detail: 'No encontrado' })
    await expect(eliminarAviso('no-existe')).rejects.toMatchObject({ status: 404 })
  })
})

describe('listarGestion', () => {
  it('returns list from GET /avisos/gestion on 200', async () => {
    mock.onGet('/avisos/gestion').reply(200, [sampleAviso])
    const result = await listarGestion()
    expect(result).toEqual([sampleAviso])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/avisos/gestion').reply(403, { detail: 'Forbidden' })
    await expect(listarGestion()).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 2.3 — feed
// ---------------------------------------------------------------------------
describe('listarFeed', () => {
  it('returns list from GET /avisos on 200', async () => {
    mock.onGet('/avisos').reply(200, [sampleAviso])
    const result = await listarFeed()
    expect(result).toEqual([sampleAviso])
  })

  it('returns empty array on empty feed', async () => {
    mock.onGet('/avisos').reply(200, [])
    const result = await listarFeed()
    expect(result).toEqual([])
  })
})

describe('listarPendientes', () => {
  it('returns list from GET /avisos/pendientes on 200', async () => {
    mock.onGet('/avisos/pendientes').reply(200, [sampleAviso])
    const result = await listarPendientes()
    expect(result).toEqual([sampleAviso])
  })
})

// ---------------------------------------------------------------------------
// Task 2.4 — ack
// ---------------------------------------------------------------------------
describe('ackAviso', () => {
  it('returns AcknowledgmentRead on 200', async () => {
    const ack = { id: 'ack-1', tenant_id: 'ten-1', aviso_id: 'av-1', usuario_id: 'usr-1', confirmado_at: '2024-03-01T10:00:00' }
    mock.onPost('/avisos/av-1/ack').reply(200, ack)
    const result = await ackAviso('av-1')
    expect(result.aviso_id).toBe('av-1')
  })

  it('throws DomainError on 403 (outside window)', async () => {
    mock.onPost('/avisos/av-1/ack').reply(403, { detail: 'Fuera de ventana' })
    await expect(ackAviso('av-1')).rejects.toMatchObject({ status: 403 })
  })

  it('throws DomainError on 404', async () => {
    mock.onPost('/avisos/no-existe/ack').reply(404, { detail: 'No encontrado' })
    await expect(ackAviso('no-existe')).rejects.toMatchObject({ status: 404 })
  })
})

// ---------------------------------------------------------------------------
// Task 2.5 — Zod schema coherence
// ---------------------------------------------------------------------------
describe('avisoFormSchema — scope-context coherence', () => {
  const base = {
    alcance: 'Global' as const,
    titulo: 'T',
    cuerpo: 'C',
    inicio_en: '2024-03-01T00:00:00',
    fin_en: '2024-04-01T00:00:00',
    orden: 100,
    activo: true,
    requiere_ack: false,
  }

  it('accepts Global alcance without context', () => {
    const result = avisoFormSchema.safeParse(base)
    expect(result.success).toBe(true)
  })

  it('rejects PorMateria without materia_id', () => {
    const result = avisoFormSchema.safeParse({ ...base, alcance: 'PorMateria' })
    expect(result.success).toBe(false)
  })

  it('accepts PorMateria with materia_id', () => {
    const result = avisoFormSchema.safeParse({ ...base, alcance: 'PorMateria', materia_id: 'mat-1' })
    expect(result.success).toBe(true)
  })

  it('rejects PorCohorte without cohorte_id', () => {
    const result = avisoFormSchema.safeParse({ ...base, alcance: 'PorCohorte' })
    expect(result.success).toBe(false)
  })

  it('rejects PorRol without rol_destino', () => {
    const result = avisoFormSchema.safeParse({ ...base, alcance: 'PorRol' })
    expect(result.success).toBe(false)
  })
})
