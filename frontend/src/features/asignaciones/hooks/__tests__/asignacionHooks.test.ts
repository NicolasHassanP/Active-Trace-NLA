/**
 * Tests for asignacionHooks — TanStack Query hooks.
 * Mocks the service. Verifies:
 *   useAsignaciones fetches and passes filters correctly
 *   useCrearAsignacion calls service and invalidates cache on success
 *   useEditarAsignacion calls service and invalidates cache on success
 *   useDarBajaAsignacion calls service and invalidates cache on success
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  useAsignaciones,
  useCrearAsignacion,
  useEditarAsignacion,
  useDarBajaAsignacion,
  useBuscarUsuariosAsignables,
} from '../asignacionHooks'
import * as service from '../../services/asignacionService'
import type { AsignacionRead, AsignacionCreate, AsignacionUpdate, UsuarioAsignable } from '../../types'

vi.mock('../../services/asignacionService')

const sampleAsignacion: AsignacionRead = {
  id: 'asgn-1',
  usuario_id: 'user-1',
  rol: 'PROFESOR',
  desde: '2026-03-01',
  hasta: null,
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  comisiones: [],
  responsable_id: null,
  estado_vigencia: 'vigente',
  created_at: '2026-03-01T10:00:00',
  updated_at: '2026-03-01T10:00:00',
}

const validCreate: AsignacionCreate = {
  usuario_id: 'user-1',
  rol: 'PROFESOR',
  desde: '2026-03-01',
}

const validUpdate: AsignacionUpdate = { rol: 'TUTOR' }

const createWrapper = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return { qc, wrapper }
}

beforeEach(() => vi.clearAllMocks())

// ── useAsignaciones ──────────────────────────────────────────────────────────

describe('useAsignaciones', () => {
  it('returns data from listarAsignaciones on success', async () => {
    vi.mocked(service.listarAsignaciones).mockResolvedValue([sampleAsignacion])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useAsignaciones({}), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleAsignacion])
    expect(service.listarAsignaciones).toHaveBeenCalledWith({})
  })

  it('passes filtros through to listarAsignaciones', async () => {
    vi.mocked(service.listarAsignaciones).mockResolvedValue([])
    const { wrapper } = createWrapper()
    renderHook(() => useAsignaciones({ rol: 'PROFESOR', usuario_id: 'user-1' }), { wrapper })
    await waitFor(() =>
      expect(service.listarAsignaciones).toHaveBeenCalledWith({
        rol: 'PROFESOR',
        usuario_id: 'user-1',
      }),
    )
  })

  it('exposes error state when the service throws', async () => {
    vi.mocked(service.listarAsignaciones).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useAsignaciones({}), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── useCrearAsignacion ───────────────────────────────────────────────────────

describe('useCrearAsignacion', () => {
  it('calls crearAsignacion and returns the created asignacion', async () => {
    vi.mocked(service.crearAsignacion).mockResolvedValue(sampleAsignacion)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCrearAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate(validCreate)
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.crearAsignacion).toHaveBeenCalledWith(validCreate)
    expect(result.current.data).toEqual(sampleAsignacion)
  })

  it('invalidates the asignaciones query on success', async () => {
    vi.mocked(service.crearAsignacion).mockResolvedValue(sampleAsignacion)
    const { qc, wrapper } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useCrearAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate(validCreate)
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['asignaciones'] })
  })

  it('exposes error state on 422', async () => {
    vi.mocked(service.crearAsignacion).mockRejectedValue({ status: 422, detail: 'Usuario no encontrado' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCrearAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate(validCreate)
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── useEditarAsignacion ──────────────────────────────────────────────────────

describe('useEditarAsignacion', () => {
  it('calls editarAsignacion with the correct id and body', async () => {
    const updated = { ...sampleAsignacion, rol: 'TUTOR' as const }
    vi.mocked(service.editarAsignacion).mockResolvedValue(updated)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useEditarAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'asgn-1', body: validUpdate })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.editarAsignacion).toHaveBeenCalledWith('asgn-1', validUpdate)
  })

  it('invalidates the asignaciones query on success', async () => {
    vi.mocked(service.editarAsignacion).mockResolvedValue(sampleAsignacion)
    const { qc, wrapper } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useEditarAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'asgn-1', body: validUpdate })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['asignaciones'] })
  })

  it('exposes error state on 404', async () => {
    vi.mocked(service.editarAsignacion).mockRejectedValue({ status: 404, detail: 'no encontrada' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useEditarAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate({ id: 'not-found', body: validUpdate })
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── useDarBajaAsignacion ─────────────────────────────────────────────────────

describe('useDarBajaAsignacion', () => {
  it('calls darBajaAsignacion with the correct id', async () => {
    vi.mocked(service.darBajaAsignacion).mockResolvedValue(undefined)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useDarBajaAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate('asgn-1')
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.darBajaAsignacion).toHaveBeenCalledWith('asgn-1')
  })

  it('invalidates the asignaciones query on success', async () => {
    vi.mocked(service.darBajaAsignacion).mockResolvedValue(undefined)
    const { qc, wrapper } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useDarBajaAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate('asgn-1')
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['asignaciones'] })
  })

  it('exposes error state on 403', async () => {
    vi.mocked(service.darBajaAsignacion).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useDarBajaAsignacion(), { wrapper })
    await act(async () => {
      result.current.mutate('asgn-1')
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── useBuscarUsuariosAsignables ──────────────────────────────────────────────

const sampleUsuario: UsuarioAsignable = {
  id: 'user-uuid-1',
  nombre: 'Ana',
  apellidos: 'García',
  email: 'ana@test.com',
}

describe('useBuscarUsuariosAsignables', () => {
  it('returns data from buscarUsuariosAsignables when q has content', async () => {
    vi.mocked(service.buscarUsuariosAsignables).mockResolvedValue([sampleUsuario])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosAsignables('ana'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleUsuario])
    expect(service.buscarUsuariosAsignables).toHaveBeenCalledWith('ana')
  })

  it('is disabled (not fetching) when q is empty string', async () => {
    vi.mocked(service.buscarUsuariosAsignables).mockResolvedValue([])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosAsignables(''), { wrapper })
    // Give it time to potentially fire
    await new Promise((r) => setTimeout(r, 50))
    expect(service.buscarUsuariosAsignables).not.toHaveBeenCalled()
    expect(result.current.isFetching).toBe(false)
  })

  it('is disabled when q is whitespace only', async () => {
    vi.mocked(service.buscarUsuariosAsignables).mockResolvedValue([])
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosAsignables('   '), { wrapper })
    await new Promise((r) => setTimeout(r, 50))
    expect(service.buscarUsuariosAsignables).not.toHaveBeenCalled()
    expect(result.current.isFetching).toBe(false)
  })

  it('exposes error state when service throws', async () => {
    vi.mocked(service.buscarUsuariosAsignables).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useBuscarUsuariosAsignables('test'), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
