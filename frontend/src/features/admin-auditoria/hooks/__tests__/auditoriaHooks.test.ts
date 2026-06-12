/**
 * Tests for auditoriaHooks — TanStack Query hooks (read-only, no mutations).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  useEventosAuditoria,
  useAccionesPorDia,
  useInteraccionesDocente,
  useInteraccionesDocenteMateria,
  useComunicacionesPorDocente,
  useUltimasAcciones,
} from '../auditoriaHooks'
import * as service from '../../services/auditoriaService'
import type { AuditEventRead, AccionesPorDiaResponse } from '../../types'

const sampleEvent: AuditEventRead = {
  id: 'evt-1', tenant_id: 'ten-1', actor_user_id: 'usr-1',
  impersonated_user_id: null, accion: 'LOGIN', modulo: 'auth',
  entidad_tipo: 'Usuario', entidad_id: null, resultado: 'ok',
  registros_afectados: null, ip: null, user_agent: null,
  before: null, after: null, created_at: '2026-06-01T00:00:00',
}

const sampleAccionesPorDia: AccionesPorDiaResponse = {
  items: [{ dia: '2026-06-01T00:00:00', total: 3 }],
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return wrapper
}

afterEach(() => vi.restoreAllMocks())

// ── useEventosAuditoria ───────────────────────────────────────────────────────

describe('useEventosAuditoria', () => {
  it('fetches events with default filtros', async () => {
    vi.spyOn(service, 'listarEventos').mockResolvedValue([sampleEvent])
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useEventosAuditoria({}), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleEvent])
  })

  it('fetches with limit/offset params', async () => {
    vi.spyOn(service, 'listarEventos').mockResolvedValue([])
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useEventosAuditoria({ limit: 20, offset: 40 }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarEventos).toHaveBeenCalledWith({ limit: 20, offset: 40 })
  })

  it('exposes error state when service throws', async () => {
    vi.spyOn(service, 'listarEventos').mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useEventosAuditoria({}), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── useAccionesPorDia ─────────────────────────────────────────────────────────

describe('useAccionesPorDia', () => {
  it('fetches acciones-por-dia', async () => {
    vi.spyOn(service, 'getAccionesPorDia').mockResolvedValue(sampleAccionesPorDia)
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useAccionesPorDia({}), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items).toHaveLength(1)
  })
})

// ── useInteraccionesDocente ───────────────────────────────────────────────────

describe('useInteraccionesDocente', () => {
  it('fetches interacciones-docente', async () => {
    vi.spyOn(service, 'getInteraccionesDocente').mockResolvedValue({ items: [] })
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useInteraccionesDocente({}), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items).toEqual([])
  })
})

// ── useInteraccionesDocenteMateria ────────────────────────────────────────────

describe('useInteraccionesDocenteMateria', () => {
  it('fetches interacciones-docente-materia', async () => {
    vi.spyOn(service, 'getInteraccionesDocenteMateria').mockResolvedValue({ items: [] })
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useInteraccionesDocenteMateria({}), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

// ── useComunicacionesPorDocente ───────────────────────────────────────────────

describe('useComunicacionesPorDocente', () => {
  it('fetches comunicaciones-por-docente', async () => {
    vi.spyOn(service, 'getComunicacionesPorDocente').mockResolvedValue({ items: [] })
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useComunicacionesPorDocente(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

// ── useUltimasAcciones ────────────────────────────────────────────────────────

describe('useUltimasAcciones', () => {
  it('fetches ultimas-acciones', async () => {
    vi.spyOn(service, 'getUltimasAcciones').mockResolvedValue([sampleEvent])
    const wrapper = makeWrapper()
    const { result } = renderHook(() => useUltimasAcciones(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleEvent])
  })
})
