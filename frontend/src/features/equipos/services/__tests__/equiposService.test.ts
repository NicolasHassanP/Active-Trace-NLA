/**
 * Tests for equiposService — stubs transport via axios-mock-adapter.
 * TDD: RED first (service not yet implemented), then GREEN.
 * Covers tasks 1.2–1.7: all service functions with happy path + error scenarios.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarMisEquipos,
  consultarEquipo,
  asignacionMasiva,
  clonarEquipo,
  vigenciaGeneral,
  exportarEquipo,
} from '../equiposService'
import type {
  MisEquiposItem,
  AsignacionMasivaRequest,
  ClonarEquipoRequest,
  VigenciaGeneralRequest,
} from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})
afterEach(() => {
  mock.reset()
})

const sampleItem: MisEquiposItem = {
  asignacion_id: 'asg-1',
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  rol: 'PROFESOR',
  desde: '2024-03-01',
  hasta: null,
  estado_vigencia: 'vigente',
  comisiones: [],
  responsable_id: null,
}

// ---------------------------------------------------------------------------
// Task 1.2 — listarMisEquipos
// ---------------------------------------------------------------------------
describe('listarMisEquipos', () => {
  it('returns list on 200', async () => {
    mock.onGet('/equipos/mis-equipos').reply(200, [sampleItem])
    const result = await listarMisEquipos()
    expect(result).toEqual([sampleItem])
  })

  it('returns empty array on 200 with empty list', async () => {
    mock.onGet('/equipos/mis-equipos').reply(200, [])
    const result = await listarMisEquipos()
    expect(result).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/equipos/mis-equipos').reply(403, { detail: 'Forbidden' })
    await expect(listarMisEquipos()).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 1.3 — consultarEquipo
// ---------------------------------------------------------------------------
describe('consultarEquipo', () => {
  it('calls GET /equipos with tripleta and returns list on 200', async () => {
    mock.onGet('/equipos').reply(200, [sampleItem])
    const result = await consultarEquipo({ materia_id: 'mat-1', carrera_id: 'car-1', cohorte_id: 'coh-1' })
    expect(result).toEqual([sampleItem])
    const params = mock.history.get[0].params
    expect(params).toMatchObject({ materia_id: 'mat-1', carrera_id: 'car-1', cohorte_id: 'coh-1' })
  })

  it('passes optional rol and responsable_id filters', async () => {
    mock.onGet('/equipos').reply(200, [sampleItem])
    await consultarEquipo({ materia_id: 'm1', carrera_id: 'c1', cohorte_id: 'coh1', rol: 'TUTOR', responsable_id: 'resp-1' })
    const params = mock.history.get[0].params
    expect(params).toMatchObject({ rol: 'TUTOR', responsable_id: 'resp-1' })
  })

  it('throws DomainError on 422', async () => {
    mock.onGet('/equipos').reply(422, { detail: 'Rol inválido' })
    await expect(consultarEquipo({ materia_id: 'm1', carrera_id: 'c1', cohorte_id: 'coh1', rol: 'INVALID' as never }))
      .rejects.toMatchObject({ status: 422 })
  })
})

// ---------------------------------------------------------------------------
// Task 1.4 — asignacionMasiva
// ---------------------------------------------------------------------------
describe('asignacionMasiva', () => {
  const body: AsignacionMasivaRequest = {
    usuario_ids: ['usr-1', 'usr-2'],
    materia_id: 'mat-1',
    carrera_id: 'car-1',
    cohorte_id: 'coh-1',
    rol: 'PROFESOR',
    desde: '2024-03-01',
  }

  it('returns ResumenLote on 201', async () => {
    mock.onPost('/equipos/asignacion-masiva').reply(201, { creadas: 2 })
    const result = await asignacionMasiva(body)
    expect(result.creadas).toBe(2)
  })

  it('throws DomainError on 422 (invalid reference)', async () => {
    mock.onPost('/equipos/asignacion-masiva').reply(422, { detail: 'Usuario no encontrado' })
    await expect(asignacionMasiva(body)).rejects.toMatchObject({ status: 422, detail: 'Usuario no encontrado' })
  })
})

// ---------------------------------------------------------------------------
// Task 1.5 — clonarEquipo
// ---------------------------------------------------------------------------
describe('clonarEquipo', () => {
  const body: ClonarEquipoRequest = {
    origen_materia_id: 'mat-1',
    origen_carrera_id: 'car-1',
    origen_cohorte_id: 'coh-2023',
    destino_materia_id: 'mat-1',
    destino_carrera_id: 'car-1',
    destino_cohorte_id: 'coh-2024',
    desde: '2024-03-01',
  }

  it('returns ResumenClonacion on 201', async () => {
    mock.onPost('/equipos/clonar').reply(201, { clonadas: 3, omitidas: 1 })
    const result = await clonarEquipo(body)
    expect(result.clonadas).toBe(3)
    expect(result.omitidas).toBe(1)
  })

  it('throws DomainError on network error', async () => {
    mock.onPost('/equipos/clonar').networkError()
    await expect(clonarEquipo(body)).rejects.toMatchObject({ status: 0 })
  })
})

// ---------------------------------------------------------------------------
// Task 1.6 — vigenciaGeneral
// ---------------------------------------------------------------------------
describe('vigenciaGeneral', () => {
  const body: VigenciaGeneralRequest = {
    materia_id: 'mat-1',
    carrera_id: 'car-1',
    cohorte_id: 'coh-1',
    desde: '2024-03-01',
  }

  it('returns VigenciaGeneralResponse with afectadas on 200', async () => {
    mock.onPatch('/equipos/vigencia-general').reply(200, { afectadas: 5 })
    const result = await vigenciaGeneral(body)
    expect(result.afectadas).toBe(5)
  })

  it('throws DomainError on 422', async () => {
    mock.onPatch('/equipos/vigencia-general').reply(422, { detail: 'hasta anterior a desde' })
    await expect(vigenciaGeneral(body)).rejects.toMatchObject({ status: 422 })
  })
})

// ---------------------------------------------------------------------------
// Task 1.7 — exportarEquipo (blob download)
// ---------------------------------------------------------------------------
describe('exportarEquipo', () => {
  it('calls GET /equipos/exportar with tripleta and returns Blob', async () => {
    const csvContent = 'asignacion_id,rol\nasg-1,PROFESOR\n'
    const blob = new Blob([csvContent], { type: 'text/csv' })
    mock.onGet('/equipos/exportar').reply(200, blob, { 'content-type': 'text/csv' })
    const result = await exportarEquipo({ materia_id: 'mat-1', carrera_id: 'car-1', cohorte_id: 'coh-1' })
    expect(result).toBeInstanceOf(Blob)
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/equipos/exportar').reply(403, { detail: 'Forbidden' })
    await expect(exportarEquipo({ materia_id: 'm1', carrera_id: 'c1', cohorte_id: 'coh1' }))
      .rejects.toMatchObject({ status: 403 })
  })
})
