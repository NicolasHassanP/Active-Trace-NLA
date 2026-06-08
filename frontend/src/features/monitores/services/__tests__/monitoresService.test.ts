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
  nombre: 'Diego',
  apellidos: 'Fernández',
  email: 'diego.fernandez@alumno.demo.com',
  comision: '1A',
  regional: 'Buenos Aires',
  actividades_detalle: [],
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
      { entrada_padron_id: 'alumno-1', estado: 'atrasado', aprobadas: 1, faltantes: 3, nombre: 'Ana', apellidos: 'López', email: 'ana@demo.com', comision: '1A', regional: 'Córdoba', actividades_detalle: [] },
      { entrada_padron_id: 'alumno-2', estado: 'al_dia', aprobadas: 4, faltantes: 0, nombre: 'Luis', apellidos: 'Gómez', email: 'luis@demo.com', comision: '2B', regional: 'Rosario', actividades_detalle: [] },
    ]
    const blob = exportarMonitorCsv(filas)
    expect(blob).toBeInstanceOf(Blob)
    expect(blob.type).toBe('text/csv')
  })

  it('CSV contains header row with human-readable column names', async () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'alumno-1', estado: 'atrasado', aprobadas: 1, faltantes: 3, nombre: 'Ana', apellidos: 'López', email: 'ana@demo.com', comision: '1A', regional: 'Córdoba', actividades_detalle: [] },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    const header = text.split('\n')[0]
    expect(header).toBe('nombre,apellidos,email,comision,regional,estado,aprobadas,faltantes,actividades_aprobadas')
  })

  it('CSV contains data rows with nombre, apellidos, email, comision, regional', async () => {
    const filas: MonitorFila[] = [
      {
        entrada_padron_id: 'alumno-uuid-1',
        estado: 'al_dia',
        aprobadas: 4,
        faltantes: 0,
        nombre: 'Diego',
        apellidos: 'Fernández',
        email: 'diego.fernandez@alumno.demo.com',
        comision: '1A',
        regional: 'Buenos Aires',
        actividades_detalle: [],
      },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    expect(text).toContain('Diego')
    expect(text).toContain('Fernández')
    expect(text).toContain('diego.fernandez@alumno.demo.com')
    expect(text).toContain('1A')
    expect(text).toContain('Buenos Aires')
    expect(text).toContain('al_dia')
    expect(text).toContain('4')
  })

  it('CSV does NOT expose raw entrada_padron_id UUID in data rows', async () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'ac5ed4b7-raw-uuid', estado: 'atrasado', aprobadas: 0, faltantes: 2, nombre: 'María', apellidos: 'Ruiz', email: 'maria@demo.com', comision: '3C', regional: 'Mendoza', actividades_detalle: [] },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    // UUID must not appear in data rows (only header + data rows after line 0)
    const dataRows = text.split('\n').slice(1).join('\n')
    expect(dataRows).not.toContain('ac5ed4b7-raw-uuid')
  })

  it('uses null-safe fallbacks (empty string) when fields are null', async () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'x', estado: 'sin_datos', aprobadas: 0, faltantes: 0, nombre: null, apellidos: null, email: null, comision: null, regional: null, actividades_detalle: [] },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    const dataLine = text.split('\n')[1]
    // All nullable fields resolve to empty string — 5 empty fields then estado
    // fields: nombre,apellidos,email,comision,regional,estado,aprobadas,faltantes,actividades_aprobadas
    expect(dataLine).toBe(',,,,,sin_datos,0,0,')
  })

  it('actividades_aprobadas lists only approved activity names joined by semicolon', async () => {
    const filas: MonitorFila[] = [
      {
        entrada_padron_id: 'x',
        estado: 'al_dia',
        aprobadas: 2,
        faltantes: 1,
        nombre: 'Carlos',
        apellidos: 'Vega',
        email: 'c@demo.com',
        comision: '1A',
        regional: 'CABA',
        actividades_detalle: [
          { actividad: 'TP1', aprobado: true, nota: '8' },
          { actividad: 'TP2', aprobado: false, nota: '3' },
          { actividad: 'TP3', aprobado: true, nota: '9' },
        ],
      },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    expect(text).toContain('TP1; TP3')
    expect(text).not.toContain('TP2')
  })

  it('escapes CSV cells that contain commas', async () => {
    const filas: MonitorFila[] = [
      { entrada_padron_id: 'x', estado: 'atrasado', aprobadas: 0, faltantes: 1, nombre: 'De la Cruz, Jr.', apellidos: 'Smith', email: 's@demo.com', comision: '1A', regional: 'Norte', actividades_detalle: [] },
    ]
    const blob = exportarMonitorCsv(filas)
    const text = await blob.text()
    expect(text).toContain('"De la Cruz, Jr."')
  })

  it('returns Blob with one header row on empty filas array', async () => {
    const blob = exportarMonitorCsv([])
    const text = await blob.text()
    const lines = text.trim().split('\n')
    expect(lines).toHaveLength(1)
    expect(lines[0]).toBe('nombre,apellidos,email,comision,regional,estado,aprobadas,faltantes,actividades_aprobadas')
  })
})
