/**
 * Tests for monitoresHooks — useMonitor with all filters in queryKey.
 * Task 4.4 — TDD: RED first.
 * Critical: queryKey MUST include ALL active filter params.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useMonitor } from '../monitoresHooks'
import * as service from '../../services/monitoresService'
import type { MonitorFila } from '../../types'

vi.mock('../../services/monitoresService')

const sampleFila: MonitorFila = {
  entrada_padron_id: 'alumno-1',
  estado: 'atrasado',
  aprobadas: 1,
  faltantes: 3,
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useMonitor', () => {
  it('returns monitor rows on success with no filters', async () => {
    vi.mocked(service.listarMonitor).mockResolvedValue([sampleFila])
    const { result } = renderHook(() => useMonitor({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleFila])
  })

  it('calls service with all provided filter params', async () => {
    vi.mocked(service.listarMonitor).mockResolvedValue([])
    const params = { materia_id: 'mat-1', regional: 'Buenos Aires', busqueda: 'García' }
    const { result } = renderHook(() => useMonitor(params), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarMonitor).toHaveBeenCalledWith(params)
  })

  it('returns empty array on empty response', async () => {
    vi.mocked(service.listarMonitor).mockResolvedValue([])
    const { result } = renderHook(() => useMonitor({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })

  it('returns error state on API failure', async () => {
    vi.mocked(service.listarMonitor).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useMonitor({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('queryKey includes materia_id filter so different filters do NOT share cache', async () => {
    vi.mocked(service.listarMonitor).mockResolvedValue([sampleFila])

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    // Render with materia_id = 'mat-1'
    const { result: r1 } = renderHook(() => useMonitor({ materia_id: 'mat-1' }), { wrapper })
    await waitFor(() => expect(r1.current.isSuccess).toBe(true))

    // Render with materia_id = 'mat-2'
    const { result: r2 } = renderHook(() => useMonitor({ materia_id: 'mat-2' }), { wrapper })
    await waitFor(() => expect(r2.current.isSuccess).toBe(true))

    // Service should have been called twice (separate cache entries)
    expect(service.listarMonitor).toHaveBeenCalledTimes(2)
    expect(service.listarMonitor).toHaveBeenCalledWith({ materia_id: 'mat-1' })
    expect(service.listarMonitor).toHaveBeenCalledWith({ materia_id: 'mat-2' })
  })

  it('queryKey includes fecha_desde and fecha_hasta for correct cache isolation', async () => {
    vi.mocked(service.listarMonitor).mockResolvedValue([])

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result: r1 } = renderHook(
      () => useMonitor({ fecha_desde: '2024-01-01', fecha_hasta: '2024-06-30' }),
      { wrapper },
    )
    await waitFor(() => expect(r1.current.isSuccess).toBe(true))

    const { result: r2 } = renderHook(
      () => useMonitor({ fecha_desde: '2024-07-01', fecha_hasta: '2024-12-31' }),
      { wrapper },
    )
    await waitFor(() => expect(r2.current.isSuccess).toBe(true))

    expect(service.listarMonitor).toHaveBeenCalledTimes(2)
  })
})
