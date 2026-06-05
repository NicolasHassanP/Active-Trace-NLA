/**
 * Tests for coloquiosService — stubs transport via axios-mock-adapter.
 * TDD: RED first, then GREEN.
 * Tasks 6.2, 6.3, 6.4, 6.5, 6.6, 6.7.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  metricas,
  listarConvocatorias,
  crearConvocatoria,
  importarCandidatos,
  cerrarConvocatoria,
  agenda,
  resultados,
} from '../coloquiosService'
import type {
  MetricasRead,
  ConvocatoriaMetricasRead,
  ConvocatoriaConTurnosRead,
  AgendaItemRead,
  ResultadoRead,
  CrearConvocatoriaRequest,
  ImportarCandidatosRequest,
} from '../../types'

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

const sampleMetricas: MetricasRead = {
  convocatorias_activas: 3,
  alumnos_cargados: 120,
  reservas_activas: 45,
  notas_registradas: 10,
}

const sampleConvocatoria: ConvocatoriaMetricasRead = {
  id: 'eval-uuid-1',
  materia_id: 'mat-uuid-1',
  cohorte_id: 'coh-uuid-1',
  tipo: 'coloquio',
  instancia: 'Primera',
  cerrada: false,
  convocados: 30,
  reservas_activas: 10,
  cupos_libres: 5,
}

const sampleCrearRequest: CrearConvocatoriaRequest = {
  materia_id: 'mat-uuid-1',
  cohorte_id: 'coh-uuid-1',
  tipo: 'coloquio',
  instancia: 'Primera',
  dias_disponibles: 2,
  turnos: [{ fecha: '2024-06-10', cupo_total: 15 }],
}

const sampleConvocatoriaConTurnos: ConvocatoriaConTurnosRead = {
  evaluacion: {
    id: 'eval-uuid-1',
    materia_id: 'mat-uuid-1',
    cohorte_id: 'coh-uuid-1',
    tipo: 'coloquio',
    instancia: 'Primera',
    dias_disponibles: 2,
    cerrada: false,
  },
  turnos: [{ id: 'turno-uuid-1', evaluacion_id: 'eval-uuid-1', fecha: '2024-06-10', cupo_total: 15, franja: null }],
}

const sampleImportarRequest: ImportarCandidatosRequest = {
  evaluacion_id: 'eval-uuid-1',
  alumno_ids: ['alumno-1', 'alumno-2'],
}

const sampleAgenda: AgendaItemRead = {
  reserva_id: 'res-uuid-1',
  evaluacion_id: 'eval-uuid-1',
  turno_id: 'turno-uuid-1',
  fecha_turno: '2024-06-10',
  alumno_id: 'alumno-1',
  estado: 'activa',
}

const sampleResultado: ResultadoRead = {
  id: 'res-uuid-1',
  evaluacion_id: 'eval-uuid-1',
  alumno_id: 'alumno-1',
  nota_final: '8',
}

// ---------------------------------------------------------------------------
// Task 6.2 — metricas
// ---------------------------------------------------------------------------

describe('metricas', () => {
  it('returns MetricasRead on 200', async () => {
    mock.onGet('/coloquios/metricas').reply(200, sampleMetricas)
    const result = await metricas()
    expect(result).toEqual(sampleMetricas)
  })

  it('returns all four metric fields', async () => {
    mock.onGet('/coloquios/metricas').reply(200, sampleMetricas)
    const result = await metricas()
    expect(result.convocatorias_activas).toBe(3)
    expect(result.alumnos_cargados).toBe(120)
    expect(result.reservas_activas).toBe(45)
    expect(result.notas_registradas).toBe(10)
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/coloquios/metricas').reply(403, { detail: 'Forbidden' })
    await expect(metricas()).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 6.3 — listarConvocatorias
// ---------------------------------------------------------------------------

describe('listarConvocatorias', () => {
  it('returns list of ConvocatoriaMetricasRead on 200', async () => {
    mock.onGet('/coloquios/convocatorias').reply(200, [sampleConvocatoria])
    const result = await listarConvocatorias()
    expect(result).toEqual([sampleConvocatoria])
  })

  it('returns empty list on 200 with no rows', async () => {
    mock.onGet('/coloquios/convocatorias').reply(200, [])
    const result = await listarConvocatorias()
    expect(result).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/coloquios/convocatorias').reply(403, { detail: 'Forbidden' })
    await expect(listarConvocatorias()).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 6.4 — crearConvocatoria
// ---------------------------------------------------------------------------

describe('crearConvocatoria', () => {
  it('returns ConvocatoriaConTurnosRead on 201', async () => {
    mock.onPost('/coloquios/convocatorias').reply(201, sampleConvocatoriaConTurnos)
    const result = await crearConvocatoria(sampleCrearRequest)
    expect(result).toEqual(sampleConvocatoriaConTurnos)
    expect(result.evaluacion.id).toBe('eval-uuid-1')
    expect(result.turnos).toHaveLength(1)
  })

  it('throws DomainError on 422 (cupo <= 0)', async () => {
    mock.onPost('/coloquios/convocatorias').reply(422, { detail: 'cupo_total debe ser mayor a 0' })
    await expect(crearConvocatoria({ ...sampleCrearRequest, turnos: [{ fecha: '2024-06-10', cupo_total: 0 }] }))
      .rejects.toMatchObject({ status: 422 })
  })

  it('throws DomainError on 403 (missing permission)', async () => {
    mock.onPost('/coloquios/convocatorias').reply(403, { detail: 'Forbidden' })
    await expect(crearConvocatoria(sampleCrearRequest)).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 6.5 — importarCandidatos
// ---------------------------------------------------------------------------

describe('importarCandidatos', () => {
  it('returns undefined on 204 (no content)', async () => {
    mock.onPost('/coloquios/convocatorias/eval-uuid-1/candidatos').reply(204)
    const result = await importarCandidatos('eval-uuid-1', sampleImportarRequest)
    expect(result).toBeUndefined()
  })

  it('throws DomainError on 422 (evaluacion_id mismatch)', async () => {
    mock.onPost('/coloquios/convocatorias/eval-uuid-1/candidatos').reply(422, {
      detail: 'evaluacion_id del body no coincide con el de la URL',
    })
    await expect(importarCandidatos('eval-uuid-1', { ...sampleImportarRequest, evaluacion_id: 'other' }))
      .rejects.toMatchObject({ status: 422 })
  })

  it('throws DomainError on 403', async () => {
    mock.onPost('/coloquios/convocatorias/eval-uuid-1/candidatos').reply(403, { detail: 'Forbidden' })
    await expect(importarCandidatos('eval-uuid-1', sampleImportarRequest)).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 6.6 — cerrarConvocatoria
// ---------------------------------------------------------------------------

describe('cerrarConvocatoria', () => {
  it('resolves on 200', async () => {
    mock.onPost('/coloquios/convocatorias/eval-uuid-1/cerrar').reply(200, { closed: true })
    await expect(cerrarConvocatoria('eval-uuid-1')).resolves.not.toThrow()
  })

  it('throws DomainError on 404 (evaluacion not found)', async () => {
    mock.onPost('/coloquios/convocatorias/eval-uuid-1/cerrar').reply(404, { detail: 'Not found' })
    await expect(cerrarConvocatoria('eval-uuid-1')).rejects.toMatchObject({ status: 404 })
  })

  it('throws DomainError on 403', async () => {
    mock.onPost('/coloquios/convocatorias/eval-uuid-1/cerrar').reply(403, { detail: 'Forbidden' })
    await expect(cerrarConvocatoria('eval-uuid-1')).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 6.7 — agenda
// ---------------------------------------------------------------------------

describe('agenda', () => {
  it('returns list of AgendaItemRead on 200', async () => {
    mock.onGet('/coloquios/agenda').reply(200, [sampleAgenda])
    const result = await agenda({})
    expect(result).toEqual([sampleAgenda])
  })

  it('passes materia_id, fecha_desde, fecha_hasta query params', async () => {
    mock.onGet('/coloquios/agenda').reply(200, [])
    await agenda({ materia_id: 'mat-1', fecha_desde: '2024-06-01', fecha_hasta: '2024-06-30' })
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({
      materia_id: 'mat-1',
      fecha_desde: '2024-06-01',
      fecha_hasta: '2024-06-30',
    })
  })

  it('omits null filter values', async () => {
    mock.onGet('/coloquios/agenda').reply(200, [])
    await agenda({ materia_id: null })
    const sentParams = mock.history.get[0].params ?? {}
    expect(sentParams).not.toHaveProperty('materia_id')
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/coloquios/agenda').reply(403, { detail: 'Forbidden' })
    await expect(agenda({})).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 6.7 — resultados
// ---------------------------------------------------------------------------

describe('resultados', () => {
  it('returns list of ResultadoRead on 200', async () => {
    mock.onGet('/coloquios/convocatorias/eval-uuid-1/resultados').reply(200, [sampleResultado])
    const result = await resultados('eval-uuid-1')
    expect(result).toEqual([sampleResultado])
  })

  it('returns empty list when no results', async () => {
    mock.onGet('/coloquios/convocatorias/eval-uuid-1/resultados').reply(200, [])
    const result = await resultados('eval-uuid-1')
    expect(result).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/coloquios/convocatorias/eval-uuid-1/resultados').reply(403, { detail: 'Forbidden' })
    await expect(resultados('eval-uuid-1')).rejects.toMatchObject({ status: 403 })
  })

  it('throws DomainError on 404 (evaluacion not found)', async () => {
    mock.onGet('/coloquios/convocatorias/nonexistent/resultados').reply(404, { detail: 'Not found' })
    await expect(resultados('nonexistent')).rejects.toMatchObject({ status: 404 })
  })
})
