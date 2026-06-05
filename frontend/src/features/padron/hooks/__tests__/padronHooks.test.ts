/**
 * Tests for Padrón TanStack Query hooks.
 * Uses a real QueryClient with test configuration.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  usePreviewPadron,
  useActivarPadron,
  useVaciarPadron,
  useSyncMoodlePadron,
} from '../padronHooks'
import * as padronService from '../../services/padronService'
import type { PadronRowDTO, VersionPadronRead } from '../../types'

vi.mock('../../services/padronService')

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

const mockRows: PadronRowDTO[] = [
  { nombre: 'Ana', apellidos: 'Paz', email: 'a@t.com', comision: 'A1', regional: 'BUE' },
]

const mockVersion: VersionPadronRead = {
  id: 'v1', materia_id: 'm1', cohorte_id: 'c1',
  total_filas: 1, activa: true, creado_en: '2026-06-05',
}

describe('usePreviewPadron', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls previewPadron with the provided file and resolves', async () => {
    vi.mocked(padronService.previewPadron).mockResolvedValue(mockRows)
    const file = new File(['data'], 'test.csv')
    const { result } = renderHook(() => usePreviewPadron(), { wrapper: createWrapper() })
    result.current.mutate(file)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockRows)
    expect(padronService.previewPadron).toHaveBeenCalledWith(file)
  })

  it('sets error state on rejection', async () => {
    vi.mocked(padronService.previewPadron).mockRejectedValue({ status: 422, detail: 'invalid' })
    const file = new File(['bad'], 'bad.csv')
    const { result } = renderHook(() => usePreviewPadron(), { wrapper: createWrapper() })
    result.current.mutate(file)
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useActivarPadron', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls activarPadron and resolves version', async () => {
    vi.mocked(padronService.activarPadron).mockResolvedValue(mockVersion)
    const { result } = renderHook(() => useActivarPadron(), { wrapper: createWrapper() })
    result.current.mutate({ materia_id: 'm1', cohorte_id: 'c1', rows: mockRows })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockVersion)
  })
})

describe('useVaciarPadron', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls vaciarPadron and resolves void', async () => {
    vi.mocked(padronService.vaciarPadron).mockResolvedValue(undefined)
    const { result } = renderHook(() => useVaciarPadron(), { wrapper: createWrapper() })
    result.current.mutate({ materia_id: 'm1', cohorte_id: 'c1' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })

  it('sets error state on 403', async () => {
    vi.mocked(padronService.vaciarPadron).mockRejectedValue({ status: 403, detail: 'no permitido' })
    const { result } = renderHook(() => useVaciarPadron(), { wrapper: createWrapper() })
    result.current.mutate({ materia_id: 'm1', cohorte_id: 'c1' })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useSyncMoodlePadron', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls syncMoodlePadron and resolves version', async () => {
    vi.mocked(padronService.syncMoodlePadron).mockResolvedValue(mockVersion)
    const { result } = renderHook(() => useSyncMoodlePadron(), { wrapper: createWrapper() })
    result.current.mutate({ course_id: 'crs1', materia_id: 'm1', cohorte_id: 'c1' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockVersion)
  })
})
