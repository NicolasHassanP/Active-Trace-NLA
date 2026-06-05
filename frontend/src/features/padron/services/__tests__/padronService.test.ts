/**
 * Tests for padronService — stubs the transport (axios-mock-adapter).
 * Covers preview, activar, vaciar, syncMoodle with multiple status cases.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  previewPadron,
  activarPadron,
  vaciarPadron,
  syncMoodlePadron,
} from '../padronService'
import type { PadronRowDTO } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

afterEach(() => {
  mock.reset()
})

const sampleRows: PadronRowDTO[] = [
  { nombre: 'Ana', apellidos: 'Gómez', email: 'ana@test.com', comision: 'A1', regional: 'BUE' },
]

describe('previewPadron', () => {
  it('sends multipart FormData and returns rows on 200', async () => {
    mock.onPost('/padron/preview').reply(200, sampleRows)
    const file = new File(['col1,col2\nval1,val2'], 'padron.csv', { type: 'text/csv' })
    const result = await previewPadron(file)
    expect(result).toEqual(sampleRows)
    // Verify multipart was used
    const req = mock.history.post[0]
    expect(req.data).toBeInstanceOf(FormData)
  })

  it('throws DomainError with detail on 422', async () => {
    mock.onPost('/padron/preview').reply(422, { detail: 'columna email faltante' })
    const file = new File(['bad data'], 'padron.csv', { type: 'text/csv' })
    await expect(previewPadron(file)).rejects.toMatchObject({
      status: 422,
      detail: 'columna email faltante',
    })
  })
})

describe('activarPadron', () => {
  it('returns VersionPadronRead on 201', async () => {
    const response = {
      id: 'v1', materia_id: 'm1', cohorte_id: 'c1',
      total_filas: 1, activa: true, creado_en: '2026-06-05T00:00:00',
    }
    mock.onPost('/padron/activar').reply(201, response)
    const result = await activarPadron({ materia_id: 'm1', cohorte_id: 'c1', rows: sampleRows })
    expect(result).toEqual(response)
  })

  it('sends body with only materia_id, cohorte_id and rows — no identity/tenant', async () => {
    const response = {
      id: 'v1', materia_id: 'm1', cohorte_id: 'c1',
      total_filas: 1, activa: true, creado_en: '2026-06-05T00:00:00',
    }
    mock.onPost('/padron/activar').reply(201, response)
    await activarPadron({ materia_id: 'm1', cohorte_id: 'c1', rows: sampleRows })
    const sentBody = JSON.parse(mock.history.post[0].data as string)
    expect(Object.keys(sentBody)).toEqual(['materia_id', 'cohorte_id', 'rows'])
  })

  it('throws DomainError on 403', async () => {
    mock.onPost('/padron/activar').reply(403, { detail: 'sin permiso' })
    await expect(
      activarPadron({ materia_id: 'm1', cohorte_id: 'c1', rows: sampleRows }),
    ).rejects.toMatchObject({ status: 403 })
  })

  it('throws DomainError on 404', async () => {
    mock.onPost('/padron/activar').reply(404, { detail: 'materia no encontrada' })
    await expect(
      activarPadron({ materia_id: 'm1', cohorte_id: 'c1', rows: sampleRows }),
    ).rejects.toMatchObject({ status: 404 })
  })
})

describe('vaciarPadron', () => {
  it('resolves on 204', async () => {
    mock.onDelete('/padron/vaciar').reply(204)
    await expect(vaciarPadron('m1', 'c1')).resolves.toBeUndefined()
  })

  it('throws DomainError on 404', async () => {
    mock.onDelete('/padron/vaciar').reply(404, { detail: 'no existe padron activo' })
    await expect(vaciarPadron('m1', 'c1')).rejects.toMatchObject({ status: 404 })
  })

  it('throws DomainError on 403', async () => {
    mock.onDelete('/padron/vaciar').reply(403, { detail: 'no puede vaciar version ajena' })
    await expect(vaciarPadron('m1', 'c1')).rejects.toMatchObject({ status: 403 })
  })
})

describe('syncMoodlePadron', () => {
  it('returns VersionPadronRead on 201', async () => {
    const response = {
      id: 'v2', materia_id: 'm1', cohorte_id: 'c1',
      total_filas: 30, activa: true, creado_en: '2026-06-05T01:00:00',
    }
    mock.onPost('/padron/sync-moodle').reply(201, response)
    const result = await syncMoodlePadron({ course_id: 'crs1', materia_id: 'm1', cohorte_id: 'c1' })
    expect(result).toEqual(response)
  })

  it('throws DomainError on 503 (Moodle not configured)', async () => {
    mock.onPost('/padron/sync-moodle').reply(503, { detail: 'Moodle no configurado' })
    await expect(
      syncMoodlePadron({ course_id: 'crs1', materia_id: 'm1', cohorte_id: 'c1' }),
    ).rejects.toMatchObject({ status: 503 })
  })

  it('throws DomainError on 502 (Moodle unavailable)', async () => {
    mock.onPost('/padron/sync-moodle').reply(502, { detail: 'Moodle no disponible' })
    await expect(
      syncMoodlePadron({ course_id: 'crs1', materia_id: 'm1', cohorte_id: 'c1' }),
    ).rejects.toMatchObject({ status: 502 })
  })
})
