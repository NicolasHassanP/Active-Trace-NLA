/**
 * Tests for perfilHooks — TanStack Query hooks.
 * Mocks the service. Verifies usePerfil fetches and useUpdatePerfil invalidates the perfil query.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { usePerfil, useUpdatePerfil } from '../perfilHooks'
import * as service from '../../services/perfilService'
import type { PerfilRead } from '../../types'

vi.mock('../../services/perfilService')

const samplePerfil: PerfilRead = {
  id: 'u-1',
  email: 'docente@test.com',
  nombre: 'Ana',
  apellidos: 'Gómez',
  dni: '30111222',
  cuil: '27-30111222-4',
  cbu: '0110599520000001234567',
  alias_cbu: 'ana.gomez.cbu',
  genero: 'F',
  legajo: 'L-001',
  legajo_profesional: 'MP-1234',
  banco: 'Nación',
  regional: 'BUE',
  facturador: true,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-06-01T00:00:00',
}

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return { qc, wrapper }
}

beforeEach(() => vi.clearAllMocks())

describe('usePerfil', () => {
  it('returns data from getPerfil on success', async () => {
    vi.mocked(service.getPerfil).mockResolvedValue(samplePerfil)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => usePerfil(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(samplePerfil)
    expect(service.getPerfil).toHaveBeenCalledOnce()
  })

  it('exposes error state when service throws', async () => {
    vi.mocked(service.getPerfil).mockRejectedValue({ status: 401, detail: 'No autenticado' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => usePerfil(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useUpdatePerfil', () => {
  it('calls updatePerfil and returns the updated perfil', async () => {
    const updated = { ...samplePerfil, nombre: 'Ana María' }
    vi.mocked(service.updatePerfil).mockResolvedValue(updated)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUpdatePerfil(), { wrapper })
    await act(async () => {
      result.current.mutate({ nombre: 'Ana María' })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.updatePerfil).toHaveBeenCalledWith({ nombre: 'Ana María' })
    expect(result.current.data).toEqual(updated)
  })

  it('invalidates the perfil query on success', async () => {
    vi.mocked(service.updatePerfil).mockResolvedValue(samplePerfil)
    const { qc, wrapper } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useUpdatePerfil(), { wrapper })
    await act(async () => {
      result.current.mutate({ nombre: 'Ana' })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['perfil'] })
  })

  it('exposes error state on 409', async () => {
    vi.mocked(service.updatePerfil).mockRejectedValue({ status: 409, detail: 'email ya usado en el tenant' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUpdatePerfil(), { wrapper })
    await act(async () => {
      result.current.mutate({ email: 'dup@test.com' })
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
