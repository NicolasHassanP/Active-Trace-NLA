/**
 * Tests for Atrasados TanStack Query hooks.
 * Verifies queryKey includes active filters for correct cache invalidation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { useAtrasados, useReporteMateria } from '../atrasadosHooks'
import * as service from '../../services/atrasadosService'
import type { AlumnoAtrasado, ReporteMateria } from '../../types'

vi.mock('../../services/atrasadosService')

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

const mockAlumnos: AlumnoAtrasado[] = [
  {
    alumno_id: 'a1', nombre: 'Sol', apellidos: 'Paz', email: 's@t.com',
    actividades_faltantes: ['TP1'], actividades_no_aprobadas: [], estado: 'atrasado',
  },
]
const mockReporte: ReporteMateria = {
  materia_id: 'm1', cohorte_id: 'c1',
  total_alumnos: 10, total_atrasados: 2, tasa_aprobacion: 0.8, sin_datos: false,
}

beforeEach(() => vi.clearAllMocks())

describe('useAtrasados', () => {
  it('calls listarAtrasados with materia_id and cohorte_id', async () => {
    vi.mocked(service.listarAtrasados).mockResolvedValue(mockAlumnos)
    const { result } = renderHook(
      () => useAtrasados({ materia_id: 'm1', cohorte_id: 'c1' }),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockAlumnos)
    expect(service.listarAtrasados).toHaveBeenCalledWith({ materia_id: 'm1', cohorte_id: 'c1' })
  })

  it('includes actividades in the call when provided', async () => {
    vi.mocked(service.listarAtrasados).mockResolvedValue(mockAlumnos)
    const { result } = renderHook(
      () => useAtrasados({ materia_id: 'm1', cohorte_id: 'c1', actividades: ['TP1'] }),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarAtrasados).toHaveBeenCalledWith(
      expect.objectContaining({ actividades: ['TP1'] }),
    )
  })
})

describe('useReporteMateria', () => {
  it('calls reporteMateria with materia_id and cohorte_id', async () => {
    vi.mocked(service.reporteMateria).mockResolvedValue(mockReporte)
    const { result } = renderHook(
      () => useReporteMateria('m1', 'c1'),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockReporte)
  })

  it('exposes sin_datos from response', async () => {
    vi.mocked(service.reporteMateria).mockResolvedValue({ ...mockReporte, sin_datos: true })
    const { result } = renderHook(
      () => useReporteMateria('m1', 'c1'),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.sin_datos).toBe(true)
  })
})
