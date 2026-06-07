/**
 * Tests for Comunicaciones hooks.
 * Covers mutations + useLoteStatus polling behavior (OQ-2).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  usePreviewComunicacion,
  useEncolarLote,
  useAprobarLote,
  useCancelarLote,
  useLoteStatus,
  useMisEnvios,
} from '../comunicacionHooks'
import * as service from '../../services/comunicacionService'
import type { LoteStatusResponse, MisEnviosResponse } from '../../types'

vi.mock('../../services/comunicacionService')

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

const mockLoteInProgress: LoteStatusResponse = {
  lote_id: 'lote1',
  mensajes: [
    { id: 'm1', lote_id: 'lote1', destinatario_email: 'a@t.com', asunto: '', cuerpo: '', estado: 'Pendiente', creado_en: '', actualizado_en: '' },
  ],
  pendientes: 1, enviados: 0, fallidos: 0, cancelados: 0,
}

const mockLoteDone: LoteStatusResponse = {
  lote_id: 'lote1',
  mensajes: [
    { id: 'm1', lote_id: 'lote1', destinatario_email: 'a@t.com', asunto: '', cuerpo: '', estado: 'Enviado', creado_en: '', actualizado_en: '' },
  ],
  pendientes: 0, enviados: 1, fallidos: 0, cancelados: 0,
}

beforeEach(() => vi.clearAllMocks())

describe('usePreviewComunicacion', () => {
  it('calls previewComunicacion and resolves rendered content', async () => {
    vi.mocked(service.previewComunicacion).mockResolvedValue({ asunto: 'Hola Ana', cuerpo: 'Texto' })
    const { result } = renderHook(() => usePreviewComunicacion(), { wrapper: createWrapper() })
    result.current.mutate({ asunto_plantilla: 'Hola {{nombre}}', cuerpo_plantilla: 'Texto', variables: { nombre: 'Ana' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.asunto).toBe('Hola Ana')
  })

  it('sets error on 422', async () => {
    vi.mocked(service.previewComunicacion).mockRejectedValue({ status: 422, detail: 'variable faltante' })
    const { result } = renderHook(() => usePreviewComunicacion(), { wrapper: createWrapper() })
    result.current.mutate({ asunto_plantilla: 'X', cuerpo_plantilla: 'X', variables: {} })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useEncolarLote', () => {
  it('calls encolarLote and returns lote_id', async () => {
    vi.mocked(service.encolarLote).mockResolvedValue({ lote_id: 'lote1', total_encolados: 3 })
    const { result } = renderHook(() => useEncolarLote(), { wrapper: createWrapper() })
    result.current.mutate({ destinatarios: [], asunto_plantilla: 'X', cuerpo_plantilla: 'X', variables_por_destinatario: {} })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.lote_id).toBe('lote1')
  })
})

describe('useAprobarLote', () => {
  it('resolves updated messages', async () => {
    vi.mocked(service.aprobarLote).mockResolvedValue([])
    const { result } = renderHook(() => useAprobarLote(), { wrapper: createWrapper() })
    result.current.mutate('lote1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

describe('useCancelarLote', () => {
  it('sets error on 409 transition', async () => {
    vi.mocked(service.cancelarLote).mockRejectedValue({ status: 409, detail: 'transicion invalida' })
    const { result } = renderHook(() => useCancelarLote(), { wrapper: createWrapper() })
    result.current.mutate('lote1')
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useLoteStatus', () => {
  it('fetches lote status and exposes data', async () => {
    vi.mocked(service.getLote).mockResolvedValue(mockLoteDone)
    const { result } = renderHook(() => useLoteStatus('lote1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.lote_id).toBe('lote1')
  })

  it('returns isTerminal=true when all messages are in terminal state', async () => {
    vi.mocked(service.getLote).mockResolvedValue(mockLoteDone)
    const { result } = renderHook(() => useLoteStatus('lote1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.isTerminal).toBe(true)
  })

  it('returns isTerminal=false when some messages are still in progress', async () => {
    vi.mocked(service.getLote).mockResolvedValue(mockLoteInProgress)
    const { result } = renderHook(() => useLoteStatus('lote1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.isTerminal).toBe(false)
  })
})

// C-27 — useMisEnvios
describe('useMisEnvios', () => {
  const mockMisEnvios: MisEnviosResponse = {
    total: 3,
    offset: 0,
    limit: 20,
    items: [
      { id: 'm1', lote_id: 'lote1', destinatario_email: 'a@t.com', asunto: 'Test', cuerpo: 'Body', estado: 'Enviado', creado_en: '', actualizado_en: '' },
    ],
  }

  it('returns data when API responds 200', async () => {
    vi.mocked(service.getMisEnvios).mockResolvedValue(mockMisEnvios)
    const { result } = renderHook(() => useMisEnvios({ offset: 0, limit: 20 }), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(3)
    expect(result.current.data?.items).toHaveLength(1)
  })

  it('sets isError=true on 403', async () => {
    vi.mocked(service.getMisEnvios).mockRejectedValue({ status: 403, detail: 'forbidden' })
    const { result } = renderHook(() => useMisEnvios(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('re-fetches when params change', async () => {
    vi.mocked(service.getMisEnvios).mockResolvedValue({ ...mockMisEnvios, total: 1 })
    const { result, rerender } = renderHook(
      ({ estado }) => useMisEnvios({ estado }),
      { wrapper: createWrapper(), initialProps: { estado: undefined as any } },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    vi.mocked(service.getMisEnvios).mockResolvedValue({ ...mockMisEnvios, total: 5 })
    rerender({ estado: 'Enviado' as any })
    await waitFor(() => expect(result.current.data?.total).toBe(5))
  })
})
