/**
 * Tests for avisosHooks — TanStack Query hooks.
 * Task 2.6.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  useAvisosGestion,
  useAvisosFeed,
  useAvisosPendientes,
  useCrearAviso,
  useActualizarAviso,
  useEliminarAviso,
  useAckAviso,
} from '../avisosHooks'
import * as service from '../../services/avisosService'
import type { AvisoRead, AcknowledgmentRead } from '../../types'

vi.mock('../../services/avisosService')

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

const sampleAviso: AvisoRead = {
  id: 'av-1', tenant_id: 'ten-1', alcance: 'Global',
  materia_id: null, cohorte_id: null, rol_destino: null,
  severidad: 'Info', titulo: 'Test', cuerpo: 'Cuerpo',
  inicio_en: '2024-03-01T00:00:00', fin_en: '2024-04-01T00:00:00',
  orden: 100, activo: true, requiere_ack: false, ack_count: 0,
}

beforeEach(() => vi.clearAllMocks())

describe('useAvisosGestion', () => {
  it('returns data from listarGestion', async () => {
    vi.mocked(service.listarGestion).mockResolvedValue([sampleAviso])
    const { result } = renderHook(() => useAvisosGestion(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleAviso])
  })

  it('exposes error when forbidden', async () => {
    vi.mocked(service.listarGestion).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useAvisosGestion(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useAvisosFeed', () => {
  it('returns data from listarFeed', async () => {
    vi.mocked(service.listarFeed).mockResolvedValue([sampleAviso])
    const { result } = renderHook(() => useAvisosFeed(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleAviso])
  })
})

describe('useAvisosPendientes', () => {
  it('returns pending avisos from listarPendientes', async () => {
    vi.mocked(service.listarPendientes).mockResolvedValue([sampleAviso])
    const { result } = renderHook(() => useAvisosPendientes(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleAviso])
  })
})

describe('useCrearAviso', () => {
  it('calls crearAviso and returns created aviso', async () => {
    vi.mocked(service.crearAviso).mockResolvedValue(sampleAviso)
    const { result } = renderHook(() => useCrearAviso(), { wrapper: createWrapper() })
    await act(async () => {
      result.current.mutate({
        alcance: 'Global', titulo: 'Test', cuerpo: 'C',
        inicio_en: '2024-03-01T00:00:00', fin_en: '2024-04-01T00:00:00',
      })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(sampleAviso)
  })
})

describe('useAckAviso', () => {
  it('calls ackAviso and returns AcknowledgmentRead', async () => {
    const ack: AcknowledgmentRead = {
      id: 'ack-1', tenant_id: 'ten-1', aviso_id: 'av-1',
      usuario_id: 'usr-1', confirmado_at: '2024-03-01T10:00:00',
    }
    vi.mocked(service.ackAviso).mockResolvedValue(ack)
    const { result } = renderHook(() => useAckAviso(), { wrapper: createWrapper() })
    await act(async () => { result.current.mutate('av-1') })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.aviso_id).toBe('av-1')
  })
})

describe('useActualizarAviso', () => {
  it('calls actualizarAviso with id and body', async () => {
    vi.mocked(service.actualizarAviso).mockResolvedValue({ ...sampleAviso, titulo: 'Nuevo' })
    const { result } = renderHook(() => useActualizarAviso(), { wrapper: createWrapper() })
    await act(async () => { result.current.mutate({ id: 'av-1', body: { titulo: 'Nuevo' } }) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.titulo).toBe('Nuevo')
  })
})

describe('useEliminarAviso', () => {
  it('calls eliminarAviso and succeeds', async () => {
    vi.mocked(service.eliminarAviso).mockResolvedValue(undefined)
    const { result } = renderHook(() => useEliminarAviso(), { wrapper: createWrapper() })
    await act(async () => { result.current.mutate('av-1') })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})
