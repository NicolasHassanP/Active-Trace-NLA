/**
 * Tests for atrasadosService — stubs transport via axios-mock-adapter.
 * Covers listarAtrasados and reporteMateria with multiple scenarios.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { listarAtrasados, reporteMateria } from '../atrasadosService'
import type { AlumnoAtrasado, ReporteMateria } from '../../types'

let mock: MockAdapter

beforeEach(() => { mock = new MockAdapter(apiClient) })
afterEach(() => { mock.reset() })

const sampleAlumnos: AlumnoAtrasado[] = [
  {
    alumno_id: 'a1', nombre: 'Luis', apellidos: 'Vera', email: 'luis@t.com',
    actividades_faltantes: ['TP1'], actividades_no_aprobadas: [], estado: 'atrasado',
  },
]

const sampleReporte: ReporteMateria = {
  materia_id: 'm1', cohorte_id: 'c1',
  total_alumnos: 30, total_atrasados: 5, tasa_aprobacion: 0.83, sin_datos: false,
}

describe('listarAtrasados', () => {
  it('returns list on 200 with materia_id and cohorte_id params', async () => {
    mock.onGet('/analisis/atrasados').reply(200, sampleAlumnos)
    const result = await listarAtrasados({ materia_id: 'm1', cohorte_id: 'c1' })
    expect(result).toEqual(sampleAlumnos)
    const params = mock.history.get[0].params
    expect(params).toMatchObject({ materia_id: 'm1', cohorte_id: 'c1' })
  })

  it('returns empty array on 200 with empty list', async () => {
    mock.onGet('/analisis/atrasados').reply(200, [])
    const result = await listarAtrasados({ materia_id: 'm1', cohorte_id: 'c1' })
    expect(result).toEqual([])
  })

  it('passes actividades array as query params when provided', async () => {
    mock.onGet('/analisis/atrasados').reply(200, sampleAlumnos)
    await listarAtrasados({ materia_id: 'm1', cohorte_id: 'c1', actividades: ['TP1', 'TP2'] })
    const params = mock.history.get[0].params
    expect(params.actividades).toEqual(['TP1', 'TP2'])
  })

  it('throws DomainError on non-200', async () => {
    mock.onGet('/analisis/atrasados').reply(403, { detail: 'sin permiso' })
    await expect(listarAtrasados({ materia_id: 'm1', cohorte_id: 'c1' }))
      .rejects.toMatchObject({ status: 403 })
  })
})

describe('reporteMateria', () => {
  it('returns ReporteMateria with sin_datos=false', async () => {
    mock.onGet('/analisis/reporte-materia').reply(200, sampleReporte)
    const result = await reporteMateria('m1', 'c1')
    expect(result).toEqual(sampleReporte)
    expect(result.sin_datos).toBe(false)
  })

  it('returns sin_datos=true when no data available', async () => {
    const noData: ReporteMateria = { ...sampleReporte, sin_datos: true, total_alumnos: 0, total_atrasados: 0, tasa_aprobacion: 0 }
    mock.onGet('/analisis/reporte-materia').reply(200, noData)
    const result = await reporteMateria('m1', 'c1')
    expect(result.sin_datos).toBe(true)
  })

  it('throws DomainError on error response', async () => {
    mock.onGet('/analisis/reporte-materia').reply(404, { detail: 'no encontrado' })
    await expect(reporteMateria('m1', 'c1')).rejects.toMatchObject({ status: 404 })
  })
})
