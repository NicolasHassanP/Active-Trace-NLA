/**
 * Tests for monitoresService — stubs transport via axios-mock-adapter.
 * TDD: RED first.
 * Tasks 4.2, 4.3:
 *   - listarMonitor: GET /api/v1/analisis/monitor with all filters
 *   - exportarMonitor: client-side CSV export from fetched rows
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { listarMonitor, exportarMonitorCsv } from '../monitoresService'
import type { MonitorFila, MonitorParams } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})
afterEach(() => {
  mock.reset()
  vi.restoreAllMocks()
})

const sampleFila: MonitorFila = {
  entrada_padron_id: 'alumno-uuid-1',
  estado: 'atrasado',
  aprobadas: 2,
  faltantes: 3,
}

// ---------------------------------------------------------------------------
// Task 4.2 — listarMonitor
// ---------------------------------------------------------------------------
describe('listarMonitor', () => {
  it('returns list of MonitorFila on 200', async () => {
    mock.onGet('/analisis/monitor').reply(200, [sampleFila])
    const result = await listarMonitor({})
    expect(result).toEqual([sampleFila])
  })

  it('returns empty list on 200 with no rows', async () => {
    mock.onGet('/analisis/monitor').reply(200, [])
    const result = await listarMonitor({})
    expect(result).toEqual([])
  })

  it('passes materia_id, regional, comision filters as query params', async () => {
    mock.onGet('/analisis/monitor').reply(200, [sampleFila])
    const params: MonitorParams = {
      materia_id: 'mat-1',
      regional: 'Buenos Aires',
      comision: 'K3055',
    }
    await listarMonitor(params)
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({
      materia_id: 'mat-1',
      regional: 'Buenos Aires',
      comision: 'K3055',
    })
  })

  it('passes busqueda, actividad, min_cumplidas filters', async () => {
    mock.onGet('/analisis/monitor').reply(200, [])
    await listarMonitor({ busqueda: 'García', actividad: 'TP1', min_cumplidas: 3 })
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({ busqueda: 'García', actividad: 'TP1', min_cumplidas: 3 })
  })

  it('passes fecha_desde and fecha_hasta filters', async () => {
    mock.onGet('/analisis/monitor').reply(200, [])
    const params: MonitorParams = {
      fecha_desde: '2024-03-01T00:00:00',
      fecha_hasta: '2024-06-30T23:59:59',
    }
    await listarMonitor(params)
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({
      fecha_desde: '2024-03-01T00:00:00',
      fecha_hasta: '2024-06-30T23:59:59',
    })
  })

  it('omits null/undefined filter values from request', async () => {
    mock.onGet('/analisis/monitor').reply(200, [])
    await listarMonitor({ materia_id: null, busqueda: null })
    const sentParams = mock.history.get[0].params ?? {}
    expect(sentParams).not.toHaveProperty('materia_id')
    expect(sentParams).not.toHaveProperty('busqueda')
  })

  it('throws DomainError on 403 (missing atrasados:ver permission)', async () => {
    mock.onGet('/analisis/monitor').reply(403, { detail: 'Forbidden' })
    await expect(listarMonitor({})).rejects.toMatchObject({ status: 403 })
  })

  it('throws DomainError on 422 (invalid date range)', async () => {
    mock.onGet('/analisis/monitor').reply(422, { detail: 'fecha_desde no puede ser posterior a fecha_hasta' })
    await expect(listarMonitor({ fecha_desde: '2024-12-01', fecha_hasta: '2024-01-01' }))
      .rejects.toMatchObject({ status: 422 })
  })
})

// ---------------------------------------------------------------------------
// Task 4.3 — exportarMonitorCsv (client-side)
// ---------------------------------------------------------------------------
describe('exportarMonitorCsv', () => {
  it('returns a CSV Blob from MonitorFila rows', () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'alumno-1', estado: 'atrasado', aprobadas: 1, faltantes: 3 },
      { entrada_padron_id: 'alumno-2', estado: 'al_dia', aprobadas: 4, faltantes: 0 },
    ]
    const blob = exportarMonitorCsv(filas)
    expect(blob).toBeInstanceOf(Blob)
    expect(blob.type).toBe('text/csv')
  })

  it('CSV contains header row with correct column names', async () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'alumno-1', estado: 'atrasado', aprobadas: 1, faltantes: 3 },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    expect(text).toContain('entrada_padron_id')
    expect(text).toContain('estado')
    expect(text).toContain('aprobadas')
    expect(text).toContain('faltantes')
  })

  it('CSV contains data rows for each MonitorFila', async () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'alumno-uuid-1', estado: 'al_dia', aprobadas: 4, faltantes: 0 },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    expect(text).toContain('alumno-uuid-1')
    expect(text).toContain('al_dia')
    expect(text).toContain('4')
  })

  it('returns Blob with one header row on empty filas array', async () => {
    const blob = exportarMonitorCsv([])
    const text = await blob.text()
    const lines = text.trim().split('\n')
    expect(lines).toHaveLength(1)
    expect(lines[0]).toContain('entrada_padron_id')
  })
})
