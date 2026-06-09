/**
 * Tests for guardiaHooks — TanStack Query hooks.
 * Mocks the service. Verifies useGuardias fetches and useRegistrarGuardia invalidates
 * the guardias query on success.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { useGuardias, useRegistrarGuardia } from '../guardiaHooks'
import * as service from '../../services/guardiaService'
import type { GuardiaRead, RegistrarGuardiaRequest } from '../../types'

vi.mock('../../services/guardiaService')

const sampleGuardia: GuardiaRead = {
  id: 'g-1',
  asignacion_id: 'a-1',
  materia_id: 'm-1',
  carrera_id: 'c-1',
  cohorte_id: 'co-1',
  dia: 'Lunes',
  horario: '10:00-12:00',
  estado: 'Pendiente',
  comentarios: '',
  creada_at: '2026-06-01T10:00:00',
}

const validBody: RegistrarGuardiaRequest = {
  materia_id: 'm-1',
  carrera_id: 'c-1',
  cohorte_id: 'co-1',
  dia: 'Lunes',
  horario: '10:00-12:00',
}

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return { qc, wrapper }
}

beforeEach(() => vi.clearAllMocks())

describe('useGuardias', () => {
  it('returns data from listarGuardias on success', async () => {
    vi.mocked(service.listarGuardias).mockResolvedValue([sampleGuardia])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useGuardias({}), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleGuardia])
    expect(service.listarGuardias).toHaveBeenCalledWith({})
  })

  it('passes the filtros through to listarGuardias', async () => {
    vi.mocked(service.listarGuardias).mockResolvedValue([])
    const { wrapper } = createWrapper()
    renderHook(() => useGuardias({ dia: 'Martes', estado: 'Realizada' }), { wrapper })
    await waitFor(() =>
      expect(service.listarGuardias).toHaveBeenCalledWith({ dia: 'Martes', estado: 'Realizada' }),
    )
  })

  it('exposes error state when the service throws', async () => {
    vi.mocked(service.listarGuardias).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useGuardias({}), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useRegistrarGuardia', () => {
  it('calls registrarGuardia and returns the created guardia', async () => {
    vi.mocked(service.registrarGuardia).mockResolvedValue(sampleGuardia)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useRegistrarGuardia(), { wrapper })
    await act(async () => {
      result.current.mutate(validBody)
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.registrarGuardia).toHaveBeenCalledWith(validBody)
    expect(result.current.data).toEqual(sampleGuardia)
  })

  it('invalidates the guardias query on success', async () => {
    vi.mocked(service.registrarGuardia).mockResolvedValue(sampleGuardia)
    const { qc, wrapper } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useRegistrarGuardia(), { wrapper })
    await act(async () => {
      result.current.mutate(validBody)
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['guardias'] })
  })

  it('exposes error state on 422', async () => {
    vi.mocked(service.registrarGuardia).mockRejectedValue({ status: 422, detail: 'horario inválido' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useRegistrarGuardia(), { wrapper })
    await act(async () => {
      result.current.mutate(validBody)
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
