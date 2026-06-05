/**
 * Tests for Tareas TanStack Query hooks.
 * Task 3.6 — TDD: RED first.
 * Covers: useMisTareas, useTareasAdmin, useDetalleTarea, mutations with invalidation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  useMisTareas,
  useTareasAdmin,
  useDetalleTarea,
  useCrearTarea,
  useDelegarTarea,
  useCambiarEstado,
  useAgregarComentario,
} from '../tareasHooks'
import * as service from '../../services/tareasService'
import type { TareaRead, ComentarioTareaRead } from '../../types'

vi.mock('../../services/tareasService')

const sampleTarea: TareaRead = {
  id: 'tarea-1',
  tenant_id: 'tenant-1',
  asignado_a: 'user-1',
  asignado_por: 'coord-1',
  descripcion: 'Revisar actas del coloquio',
  estado: 'Pendiente',
  materia_id: 'mat-1',
  contexto_id: null,
  contexto_tipo: null,
  created_at: '2024-06-01T10:00:00Z',
  updated_at: '2024-06-01T10:00:00Z',
  deleted_at: null,
}

const sampleComentario: ComentarioTareaRead = {
  id: 'com-1',
  tenant_id: 'tenant-1',
  tarea_id: 'tarea-1',
  autor_id: 'user-1',
  cuerpo: 'Revisado',
  es_sistema: false,
  created_at: '2024-06-01T11:00:00Z',
  updated_at: '2024-06-01T11:00:00Z',
  deleted_at: null,
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
// useMisTareas
// ---------------------------------------------------------------------------
describe('useMisTareas', () => {
  it('returns tasks list on success', async () => {
    vi.mocked(service.listarMias).mockResolvedValue([sampleTarea])
    const { result } = renderHook(() => useMisTareas(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleTarea])
  })

  it('returns error state on API failure', async () => {
    vi.mocked(service.listarMias).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useMisTareas(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ---------------------------------------------------------------------------
// useTareasAdmin — queryKey includes all filters
// ---------------------------------------------------------------------------
describe('useTareasAdmin', () => {
  it('fetches admin list and succeeds', async () => {
    vi.mocked(service.listarAdmin).mockResolvedValue([sampleTarea])
    const { result } = renderHook(() => useTareasAdmin({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleTarea])
  })

  it('passes filter params to the service', async () => {
    vi.mocked(service.listarAdmin).mockResolvedValue([])
    const { result } = renderHook(
      () => useTareasAdmin({ estado: 'EnProgreso', q: 'coloquio' }),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarAdmin).toHaveBeenCalledWith({ estado: 'EnProgreso', q: 'coloquio' })
  })

  it('returns empty array on empty response', async () => {
    vi.mocked(service.listarAdmin).mockResolvedValue([])
    const { result } = renderHook(() => useTareasAdmin({}), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// useDetalleTarea
// ---------------------------------------------------------------------------
describe('useDetalleTarea', () => {
  it('fetches single tarea by id', async () => {
    vi.mocked(service.detalleTarea).mockResolvedValue(sampleTarea)
    const { result } = renderHook(() => useDetalleTarea('tarea-1'), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(sampleTarea)
  })

  it('is disabled when tareaId is empty string', () => {
    const { result } = renderHook(() => useDetalleTarea(''), { wrapper: makeWrapper() })
    expect(result.current.status).toBe('pending')
    expect(service.detalleTarea).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// useCrearTarea mutation
// ---------------------------------------------------------------------------
describe('useCrearTarea', () => {
  it('calls crearTarea and succeeds', async () => {
    vi.mocked(service.crearTarea).mockResolvedValue(sampleTarea)
    const { result } = renderHook(() => useCrearTarea(), { wrapper: makeWrapper() })
    result.current.mutate({ asignado_a: 'user-1', descripcion: 'Revisar' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(sampleTarea)
  })
})

// ---------------------------------------------------------------------------
// useDelegarTarea mutation
// ---------------------------------------------------------------------------
describe('useDelegarTarea', () => {
  it('calls delegarTarea and returns updated tarea', async () => {
    const delegated = { ...sampleTarea, asignado_a: 'user-2' }
    vi.mocked(service.delegarTarea).mockResolvedValue(delegated)
    const { result } = renderHook(() => useDelegarTarea(), { wrapper: makeWrapper() })
    result.current.mutate({ tareaId: 'tarea-1', body: { asignado_a: 'user-2' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.asignado_a).toBe('user-2')
  })
})

// ---------------------------------------------------------------------------
// useCambiarEstado mutation
// ---------------------------------------------------------------------------
describe('useCambiarEstado', () => {
  it('calls cambiarEstado and returns updated tarea', async () => {
    const updated = { ...sampleTarea, estado: 'EnProgreso' as const }
    vi.mocked(service.cambiarEstado).mockResolvedValue(updated)
    const { result } = renderHook(() => useCambiarEstado(), { wrapper: makeWrapper() })
    result.current.mutate({ tareaId: 'tarea-1', body: { estado: 'EnProgreso' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.estado).toBe('EnProgreso')
  })
})

// ---------------------------------------------------------------------------
// useAgregarComentario mutation
// ---------------------------------------------------------------------------
describe('useAgregarComentario', () => {
  it('calls agregarComentario and returns created comment', async () => {
    vi.mocked(service.agregarComentario).mockResolvedValue(sampleComentario)
    const { result } = renderHook(() => useAgregarComentario(), { wrapper: makeWrapper() })
    result.current.mutate({ tareaId: 'tarea-1', body: { cuerpo: 'Revisado' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(sampleComentario)
  })
})
