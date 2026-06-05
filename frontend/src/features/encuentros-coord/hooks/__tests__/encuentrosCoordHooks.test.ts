/**
 * Tests for encuentrosCoordHooks — useInstancias and useGuardias with filters in queryKey.
 * Task 5.5 — TDD: RED first, then GREEN.
 * Verifies:
 *   - Successful fetch returns data
 *   - queryKey isolates different filter combinations
 *   - Error state surfaces correctly
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useInstancias, useGuardias } from '../encuentrosCoordHooks'
import * as service from '../../services/encuentrosCoordService'
import type { InstanciaEncuentroRead, GuardiaRead } from '../../types'

vi.mock('../../services/encuentrosCoordService')

const sampleInstancia: InstanciaEncuentroRead = {
  id: 'inst-1',
  slot_id: 'slot-1',
  materia_id: 'mat-1',
  fecha: '2024-04-10',
  hora: '18:00:00',
  titulo: 'Clase 1',
  estado: 'programado',
  meet_url: null,
  video_url: null,
  comentario: '',
}

const sampleGuardia: GuardiaRead = {
  id: 'guardia-1',
  asignacion_id: 'asig-1',
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  dia: 'lunes',
  horario: '10:00 - 12:00',
  estado: 'Pendiente',
  comentarios: '',
  creada_at: '2024-04-01T10:00:00',
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
// useInstancias
// ---------------------------------------------------------------------------

describe('useInstancias', () => {
  it('returns instancias on success with no filters', async () => {
    vi.mocked(service.listarInstancias).mockResolvedValue([sampleInstancia])
    const { result } = renderHook(() => useInstancias({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleInstancia])
  })

  it('returns empty array on empty response', async () => {
    vi.mocked(service.listarInstancias).mockResolvedValue([])
    const { result } = renderHook(() => useInstancias({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })

  it('returns error state on API failure', async () => {
    vi.mocked(service.listarInstancias).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useInstancias({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('queryKey isolates different materia_id filters', async () => {
    vi.mocked(service.listarInstancias).mockResolvedValue([sampleInstancia])
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result: r1 } = renderHook(() => useInstancias({ materia_id: 'mat-1' }), { wrapper })
    await waitFor(() => expect(r1.current.isSuccess).toBe(true))

    const { result: r2 } = renderHook(() => useInstancias({ materia_id: 'mat-2' }), { wrapper })
    await waitFor(() => expect(r2.current.isSuccess).toBe(true))

    expect(service.listarInstancias).toHaveBeenCalledTimes(2)
    expect(service.listarInstancias).toHaveBeenCalledWith({ materia_id: 'mat-1' })
    expect(service.listarInstancias).toHaveBeenCalledWith({ materia_id: 'mat-2' })
  })
})

// ---------------------------------------------------------------------------
// useGuardias
// ---------------------------------------------------------------------------

describe('useGuardias', () => {
  it('returns guardias on success with no filters', async () => {
    vi.mocked(service.listarGuardias).mockResolvedValue([sampleGuardia])
    const { result } = renderHook(() => useGuardias({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleGuardia])
  })

  it('calls service with all provided filter params', async () => {
    vi.mocked(service.listarGuardias).mockResolvedValue([])
    const params = { materia_id: 'mat-1', dia: 'lunes', estado: 'Pendiente' }
    const { result } = renderHook(() => useGuardias(params), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarGuardias).toHaveBeenCalledWith(params)
  })

  it('returns error state on API failure', async () => {
    vi.mocked(service.listarGuardias).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useGuardias({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('queryKey isolates different dia and estado filter combos', async () => {
    vi.mocked(service.listarGuardias).mockResolvedValue([])
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children)

    const { result: r1 } = renderHook(() => useGuardias({ dia: 'lunes' }), { wrapper })
    await waitFor(() => expect(r1.current.isSuccess).toBe(true))

    const { result: r2 } = renderHook(() => useGuardias({ dia: 'martes' }), { wrapper })
    await waitFor(() => expect(r2.current.isSuccess).toBe(true))

    expect(service.listarGuardias).toHaveBeenCalledTimes(2)
  })
})
