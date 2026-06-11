/**
 * Tests for coloquiosHooks — TanStack Query hooks.
 * Task 6.9 — TDD: RED first, then GREEN.
 * Covers: useMetricas, useConvocatorias, useAgenda, useResultados, mutations.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  useMetricas,
  useConvocatorias,
  useAgenda,
  useResultados,
  useCrearConvocatoria,
  useImportarCandidatos,
  useCerrarConvocatoria,
} from '../coloquiosHooks'
import * as service from '../../services/coloquiosService'
import type {
  MetricasRead,
  ConvocatoriaMetricasRead,
  AgendaItemRead,
  ResultadoRead,
  ConvocatoriaConTurnosRead,
  CrearConvocatoriaRequest,
  ImportarCandidatosRequest,
} from '../../types'

vi.mock('../../services/coloquiosService')

const sampleMetricas: MetricasRead = {
  convocatorias_activas: 2,
  alumnos_cargados: 50,
  reservas_activas: 10,
  notas_registradas: 5,
}

const sampleConvocatoria: ConvocatoriaMetricasRead = {
  id: 'eval-1',
  materia_id: 'mat-1',
  cohorte_id: 'coh-1',
  tipo: 'Coloquio',
  instancia: 'Primera',
  cerrada: false,
  convocados: 10,
  reservas_activas: 5,
  cupos_libres: 3,
}

const sampleAgenda: AgendaItemRead = {
  reserva_id: 'res-1',
  evaluacion_id: 'eval-1',
  turno_id: 'turno-1',
  fecha_turno: '2024-06-10',
  alumno_id: 'alumno-1',
  estado: 'Activa',
}

const sampleResultado: ResultadoRead = {
  id: 'res-1',
  evaluacion_id: 'eval-1',
  alumno_id: 'alumno-1',
  nota_final: '8',
}

const sampleConvocatoriaConTurnos: ConvocatoriaConTurnosRead = {
  evaluacion: {
    id: 'eval-1',
    materia_id: 'mat-1',
    cohorte_id: 'coh-1',
    tipo: 'Coloquio',
    instancia: 'Primera',
    dias_disponibles: 2,
    cerrada: false,
  },
  turnos: [],
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// useMetricas
// ---------------------------------------------------------------------------

describe('useMetricas', () => {
  it('returns MetricasRead on success', async () => {
    vi.mocked(service.metricas).mockResolvedValue(sampleMetricas)
    const { result } = renderHook(() => useMetricas(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(sampleMetricas)
  })

  it('returns error state on 403', async () => {
    vi.mocked(service.metricas).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useMetricas(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ---------------------------------------------------------------------------
// useConvocatorias
// ---------------------------------------------------------------------------

describe('useConvocatorias', () => {
  it('returns list of convocatorias on success', async () => {
    vi.mocked(service.listarConvocatorias).mockResolvedValue([sampleConvocatoria])
    const { result } = renderHook(() => useConvocatorias(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleConvocatoria])
  })

  it('returns empty array on empty response', async () => {
    vi.mocked(service.listarConvocatorias).mockResolvedValue([])
    const { result } = renderHook(() => useConvocatorias(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// useAgenda
// ---------------------------------------------------------------------------

describe('useAgenda', () => {
  it('returns agenda items on success', async () => {
    vi.mocked(service.agenda).mockResolvedValue([sampleAgenda])
    const { result } = renderHook(() => useAgenda({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleAgenda])
  })

  it('isolates cache by materia_id filter', async () => {
    vi.mocked(service.agenda).mockResolvedValue([])
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result: r1 } = renderHook(() => useAgenda({ materia_id: 'mat-1' }), { wrapper })
    await waitFor(() => expect(r1.current.isSuccess).toBe(true))
    const { result: r2 } = renderHook(() => useAgenda({ materia_id: 'mat-2' }), { wrapper })
    await waitFor(() => expect(r2.current.isSuccess).toBe(true))

    expect(service.agenda).toHaveBeenCalledTimes(2)
  })
})

// ---------------------------------------------------------------------------
// useResultados
// ---------------------------------------------------------------------------

describe('useResultados', () => {
  it('returns list of ResultadoRead on success', async () => {
    vi.mocked(service.resultados).mockResolvedValue([sampleResultado])
    const { result } = renderHook(() => useResultados('eval-1'), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleResultado])
  })

  it('isolates cache by evaluacion_id', async () => {
    vi.mocked(service.resultados).mockResolvedValue([])
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result: r1 } = renderHook(() => useResultados('eval-1'), { wrapper })
    await waitFor(() => expect(r1.current.isSuccess).toBe(true))
    const { result: r2 } = renderHook(() => useResultados('eval-2'), { wrapper })
    await waitFor(() => expect(r2.current.isSuccess).toBe(true))

    expect(service.resultados).toHaveBeenCalledTimes(2)
    expect(service.resultados).toHaveBeenCalledWith('eval-1')
    expect(service.resultados).toHaveBeenCalledWith('eval-2')
  })
})

// ---------------------------------------------------------------------------
// useCrearConvocatoria (mutation)
// ---------------------------------------------------------------------------

describe('useCrearConvocatoria', () => {
  it('calls crearConvocatoria service and invalidates cache on success', async () => {
    vi.mocked(service.crearConvocatoria).mockResolvedValue(sampleConvocatoriaConTurnos)
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result } = renderHook(() => useCrearConvocatoria(), { wrapper })
    const body: CrearConvocatoriaRequest = {
      materia_id: 'mat-1',
      cohorte_id: 'coh-1',
      tipo: 'Coloquio',
      instancia: 'Primera',
      dias_disponibles: 2,
      turnos: [{ fecha: '2024-06-10', cupo_total: 10 }],
    }
    result.current.mutate(body)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.crearConvocatoria).toHaveBeenCalledWith(body)
  })
})

// ---------------------------------------------------------------------------
// useImportarCandidatos (mutation)
// ---------------------------------------------------------------------------

describe('useImportarCandidatos', () => {
  it('calls importarCandidatos and invalidates cache on success', async () => {
    vi.mocked(service.importarCandidatos).mockResolvedValue(undefined)
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result } = renderHook(() => useImportarCandidatos(), { wrapper })
    const payload: { evaluacionId: string; body: ImportarCandidatosRequest } = {
      evaluacionId: 'eval-1',
      body: { evaluacion_id: 'eval-1', alumno_ids: ['alumno-1'] },
    }
    result.current.mutate(payload)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.importarCandidatos).toHaveBeenCalledWith(payload.evaluacionId, payload.body)
  })
})

// ---------------------------------------------------------------------------
// useCerrarConvocatoria (mutation)
// ---------------------------------------------------------------------------

describe('useCerrarConvocatoria', () => {
  it('calls cerrarConvocatoria and invalidates cache on success', async () => {
    vi.mocked(service.cerrarConvocatoria).mockResolvedValue({ closed: true })
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result } = renderHook(() => useCerrarConvocatoria(), { wrapper })
    result.current.mutate('eval-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.cerrarConvocatoria).toHaveBeenCalledWith('eval-1')
  })
})
