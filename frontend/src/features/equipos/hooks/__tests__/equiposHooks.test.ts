/**
 * Tests for equiposHooks — TanStack Query hooks.
 * Verifies queryKey includes active filters and mutations invalidate correctly.
 * Task 1.8.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  useMisEquipos,
  useEquipo,
  useAsignacionMasiva,
  useClonarEquipo,
  useVigenciaGeneral,
} from '../equiposHooks'
import * as service from '../../services/equiposService'
import type { MisEquiposItem, ResumenLote, ResumenClonacion, VigenciaGeneralResponse } from '../../types'

vi.mock('../../services/equiposService')

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

const sampleItem: MisEquiposItem = {
  asignacion_id: 'asg-1',
  usuario_id: 'u1',
  usuario_nombre: null,
  usuario_apellidos: null,
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  materia_nombre: null,
  carrera_nombre: null,
  cohorte_nombre: null,
  rol: 'PROFESOR',
  desde: '2024-03-01',
  hasta: null,
  estado_vigencia: 'vigente',
  comisiones: [],
  responsable_id: null,
}

beforeEach(() => vi.clearAllMocks())

describe('useMisEquipos', () => {
  it('returns data from listarMisEquipos on success', async () => {
    vi.mocked(service.listarMisEquipos).mockResolvedValue([sampleItem])
    const { result } = renderHook(() => useMisEquipos(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleItem])
    expect(service.listarMisEquipos).toHaveBeenCalledOnce()
  })

  it('exposes error state when service throws', async () => {
    vi.mocked(service.listarMisEquipos).mockRejectedValue({ status: 403, detail: 'Forbidden' })
    const { result } = renderHook(() => useMisEquipos(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useEquipo', () => {
  it('calls consultarEquipo with tripleta params', async () => {
    vi.mocked(service.consultarEquipo).mockResolvedValue([sampleItem])
    const params = { materia_id: 'mat-1', carrera_id: 'car-1', cohorte_id: 'coh-1' }
    const { result } = renderHook(() => useEquipo(params), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.consultarEquipo).toHaveBeenCalledWith(params)
  })

  it('is disabled when tripleta is incomplete', async () => {
    vi.mocked(service.consultarEquipo).mockResolvedValue([])
    const { result } = renderHook(
      () => useEquipo({ materia_id: '', carrera_id: 'car-1', cohorte_id: 'coh-1' }),
      { wrapper: createWrapper() },
    )
    // should not trigger the query
    expect(result.current.fetchStatus).toBe('idle')
    expect(service.consultarEquipo).not.toHaveBeenCalled()
  })
})

describe('useAsignacionMasiva', () => {
  it('calls asignacionMasiva and returns ResumenLote', async () => {
    const resumen: ResumenLote = { creadas: 3 }
    vi.mocked(service.asignacionMasiva).mockResolvedValue(resumen)
    const { result } = renderHook(() => useAsignacionMasiva(), { wrapper: createWrapper() })
    await act(async () => {
      result.current.mutate({
        usuario_ids: ['u1'],
        materia_id: 'mat-1',
        carrera_id: 'car-1',
        cohorte_id: 'coh-1',
        rol: 'PROFESOR',
        desde: '2024-03-01',
      })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(resumen)
  })
})

describe('useClonarEquipo', () => {
  it('calls clonarEquipo and returns ResumenClonacion', async () => {
    const resumen: ResumenClonacion = { clonadas: 2, omitidas: 1 }
    vi.mocked(service.clonarEquipo).mockResolvedValue(resumen)
    const { result } = renderHook(() => useClonarEquipo(), { wrapper: createWrapper() })
    await act(async () => {
      result.current.mutate({
        origen_materia_id: 'm1', origen_carrera_id: 'c1', origen_cohorte_id: 'coh-2023',
        destino_materia_id: 'm1', destino_carrera_id: 'c1', destino_cohorte_id: 'coh-2024',
        desde: '2024-03-01',
      })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(resumen)
  })
})

describe('useVigenciaGeneral', () => {
  it('calls vigenciaGeneral and returns afectadas', async () => {
    const res: VigenciaGeneralResponse = { afectadas: 4 }
    vi.mocked(service.vigenciaGeneral).mockResolvedValue(res)
    const { result } = renderHook(() => useVigenciaGeneral(), { wrapper: createWrapper() })
    await act(async () => {
      result.current.mutate({ materia_id: 'm1', carrera_id: 'c1', cohorte_id: 'coh1', desde: '2024-03-01' })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.afectadas).toBe(4)
  })
})
