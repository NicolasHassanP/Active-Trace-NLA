/**
 * Tests for useBuscarUsuariosInbox — TanStack Query hook.
 * Verifies: correct endpoint, enabled guard, error handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { useBuscarUsuariosInbox } from '../mensajeriaHooks'
import * as service from '../../services/inboxUsuariosService'
import type { UsuarioAsignable } from '@/features/asignaciones/types'

vi.mock('../../services/inboxUsuariosService')

const sampleUsuario: UsuarioAsignable = {
  id: 'user-inbox-1',
  nombre: 'Laura',
  apellidos: 'Martínez',
  email: 'laura@test.com',
  legajo: 'L-001',
}

const createWrapper = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return { qc, wrapper }
}

beforeEach(() => vi.clearAllMocks())

describe('useBuscarUsuariosInbox', () => {
  it('calls buscarUsuariosInbox with the query string and returns results', async () => {
    vi.mocked(service.buscarUsuariosInbox).mockResolvedValue([sampleUsuario])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosInbox('laura'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleUsuario])
    expect(service.buscarUsuariosInbox).toHaveBeenCalledWith('laura')
  })

  it('is disabled (not fetching) when q is empty string', async () => {
    vi.mocked(service.buscarUsuariosInbox).mockResolvedValue([])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosInbox(''), { wrapper })
    await new Promise((r) => setTimeout(r, 50))
    expect(service.buscarUsuariosInbox).not.toHaveBeenCalled()
    expect(result.current.isFetching).toBe(false)
  })

  it('is disabled when q is whitespace only', async () => {
    vi.mocked(service.buscarUsuariosInbox).mockResolvedValue([])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosInbox('   '), { wrapper })
    await new Promise((r) => setTimeout(r, 50))
    expect(service.buscarUsuariosInbox).not.toHaveBeenCalled()
    expect(result.current.isFetching).toBe(false)
  })

  it('pega al endpoint /inbox/usuarios (verificado vía el servicio mockeado)', async () => {
    vi.mocked(service.buscarUsuariosInbox).mockResolvedValue([sampleUsuario])
    const { wrapper } = createWrapper()
    renderHook(() => useBuscarUsuariosInbox('test'), { wrapper })
    await waitFor(() => expect(service.buscarUsuariosInbox).toHaveBeenCalledWith('test'))
    // The service function is what calls /inbox/usuarios — the hook delegates to it.
    // Endpoint correctness is validated in the service test (axios-mock-adapter).
  })

  it('exposes error state when service throws', async () => {
    vi.mocked(service.buscarUsuariosInbox).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosInbox('error'), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
