/**
 * Tests for guardiaService — stubs the transport (axios-mock-adapter).
 * Covers POST /guardias, GET /guardias, GET /guardias/export with success + error cases.
 * Identity (asignacion_id/tenant_id) never travels in the POST body — that is the contract.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { registrarGuardia, listarGuardias, exportarGuardias } from '../guardiaService'
import type { GuardiaRead, RegistrarGuardiaRequest } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

afterEach(() => {
  mock.reset()
})

const sampleGuardia: GuardiaRead = {
  id: 'g-1',
  asignacion_id: 'a-1',
  materia_id: 'm-1',
  carrera_id: 'c-1',
  cohorte_id: 'co-1',
  dia: 'Lunes',
  horario: '10:00-12:00',
  estado: 'Pendiente',
  comentarios: 'Aula 5',
  creada_at: '2026-06-01T10:00:00',
}

const validBody: RegistrarGuardiaRequest = {
  materia_id: 'm-1',
  carrera_id: 'c-1',
  cohorte_id: 'co-1',
  dia: 'Lunes',
  horario: '10:00-12:00',
  estado: 'Pendiente',
  comentarios: 'Aula 5',
}

describe('registrarGuardia', () => {
  it('returns GuardiaRead on 201', async () => {
    mock.onPost('/guardias').reply(201, sampleGuardia)
    const result = await registrarGuardia(validBody)
    expect(result).toEqual(sampleGuardia)
  })

  it('sends the declared fields and never asignacion_id/tenant_id', async () => {
    mock.onPost('/guardias').reply(201, sampleGuardia)
    await registrarGuardia(validBody)
    const sentBody = JSON.parse(mock.history.post[0].data as string)
    expect(sentBody).toMatchObject(validBody)
    expect(sentBody).not.toHaveProperty('asignacion_id')
    expect(sentBody).not.toHaveProperty('tenant_id')
  })

  it('throws DomainError on 422 (validación)', async () => {
    mock.onPost('/guardias').reply(422, { detail: 'horario inválido' })
    await expect(registrarGuardia(validBody)).rejects.toMatchObject({ status: 422 })
  })

  it('throws DomainError on 403 (sin permiso encuentros:gestionar)', async () => {
    mock.onPost('/guardias').reply(403, { detail: 'sin permiso' })
    await expect(registrarGuardia(validBody)).rejects.toMatchObject({ status: 403 })
  })
})

describe('listarGuardias', () => {
  it('returns GuardiaRead[] on 200 with no filters', async () => {
    mock.onGet('/guardias').reply(200, [sampleGuardia])
    const result = await listarGuardias({})
    expect(result).toEqual([sampleGuardia])
  })

  it('forwards only the provided filters as query params', async () => {
    mock.onGet('/guardias').reply(200, [sampleGuardia])
    await listarGuardias({ dia: 'Lunes', estado: 'Pendiente', materia_id: 'm-1' })
    const sentParams = mock.history.get[0].params as Record<string, string>
    expect(sentParams).toEqual({ dia: 'Lunes', estado: 'Pendiente', materia_id: 'm-1' })
    expect(sentParams).not.toHaveProperty('carrera_id')
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/guardias').reply(403, { detail: 'sin permiso' })
    await expect(listarGuardias({})).rejects.toMatchObject({ status: 403 })
  })
})

describe('exportarGuardias', () => {
  it('returns a Blob on 200', async () => {
    const csv = 'dia,horario\nLunes,10:00-12:00\n'
    mock.onGet('/guardias/export').reply(200, new Blob([csv], { type: 'text/csv' }))
    const result = await exportarGuardias({})
    expect(result).toBeInstanceOf(Blob)
  })

  it('forwards filters as query params', async () => {
    mock.onGet('/guardias/export').reply(200, new Blob([''], { type: 'text/csv' }))
    await exportarGuardias({ estado: 'Realizada' })
    const sentParams = mock.history.get[0].params as Record<string, string>
    expect(sentParams).toEqual({ estado: 'Realizada' })
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/guardias/export').reply(403, { detail: 'sin permiso' })
    await expect(exportarGuardias({})).rejects.toMatchObject({ status: 403 })
  })
})
