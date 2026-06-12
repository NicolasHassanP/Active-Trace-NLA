/**
 * Tests for estructuraHooks — TanStack Query hooks for admin-estructura.
 * Uses createElement (no JSX) so the file stays .ts.
 * Covers: query fetching, mutation calls, cache invalidation per entity.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  useCarreras,
  useMaterias,
  useCohortes,
  useCrearCarrera,
  useEditarCarrera,
  useDarBajaCarrera,
  useCrearMateria,
  useEditarMateria,
  useDarBajaMateria,
  useCrearCohorte,
  useEditarCohorte,
  useDarBajaCohorte,
} from '../estructuraHooks'
import * as service from '../../services/estructuraAdminService'
import type { CarreraRead, MateriaRead, CohorteRead } from '../../types'

// ── Fixtures ────────────────────────────────────────────────────────────────

const sampleCarrera: CarreraRead = {
  id: 'car-1', codigo: 'C1', nombre: 'Carrera 1', estado: 'activa',
  created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00',
}
const sampleMateria: MateriaRead = {
  id: 'mat-1', codigo: 'M1', nombre: 'Materia 1', estado: 'activa',
  created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00',
}
const sampleCohorte: CohorteRead = {
  id: 'coh-1', carrera_id: 'car-1', nombre: '2026', anio: 2026,
  vig_desde: '2026-03-01', vig_hasta: null, estado: 'activa',
  created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00',
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return { qc, wrapper }
}

afterEach(() => vi.restoreAllMocks())

// ── useCarreras ──────────────────────────────────────────────────────────────

describe('useCarreras', () => {
  it('fetches and returns carreras', async () => {
    vi.spyOn(service, 'listarCarreras').mockResolvedValue([sampleCarrera])
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCarreras(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleCarrera])
  })

  it('exposes error when service throws', async () => {
    vi.spyOn(service, 'listarCarreras').mockRejectedValue({ status: 403, detail: 'sin permiso' })
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCarreras(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ── useMaterias ──────────────────────────────────────────────────────────────

describe('useMaterias', () => {
  it('fetches and returns materias', async () => {
    vi.spyOn(service, 'listarMaterias').mockResolvedValue([sampleMateria])
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMaterias(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleMateria])
  })
})

// ── useCohortes ──────────────────────────────────────────────────────────────

describe('useCohortes', () => {
  it('fetches cohortes without filter', async () => {
    vi.spyOn(service, 'listarCohortes').mockResolvedValue([sampleCohorte])
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCohortes(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarCohortes).toHaveBeenCalledWith(undefined)
  })

  it('passes carrera_id filter to the service', async () => {
    vi.spyOn(service, 'listarCohortes').mockResolvedValue([sampleCohorte])
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useCohortes('car-1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(service.listarCohortes).toHaveBeenCalledWith('car-1')
  })
})

// ── useCrearCarrera ───────────────────────────────────────────────────────────

describe('useCrearCarrera', () => {
  it('calls crearCarrera and invalidates carreras on success', async () => {
    vi.spyOn(service, 'crearCarrera').mockResolvedValue(sampleCarrera)
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useCrearCarrera(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ codigo: 'C1', nombre: 'Carrera 1' })
    })

    expect(service.crearCarrera).toHaveBeenCalledOnce()
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'carreras'],
    }))
  })
})

// ── useEditarCarrera ──────────────────────────────────────────────────────────

describe('useEditarCarrera', () => {
  it('calls editarCarrera with id+body and invalidates', async () => {
    vi.spyOn(service, 'editarCarrera').mockResolvedValue(sampleCarrera)
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useEditarCarrera(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({ id: 'car-1', body: { nombre: 'Updated' } })
    })
    expect(service.editarCarrera).toHaveBeenCalledWith('car-1', { nombre: 'Updated' })
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'carreras'],
    }))
  })
})

// ── useDarBajaCarrera ─────────────────────────────────────────────────────────

describe('useDarBajaCarrera', () => {
  it('calls darBajaCarrera and invalidates', async () => {
    vi.spyOn(service, 'darBajaCarrera').mockResolvedValue()
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useDarBajaCarrera(), { wrapper })

    await act(async () => { await result.current.mutateAsync('car-1') })
    expect(service.darBajaCarrera).toHaveBeenCalledWith('car-1')
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'carreras'],
    }))
  })
})

// ── useCrearMateria ───────────────────────────────────────────────────────────

describe('useCrearMateria', () => {
  it('calls crearMateria and invalidates materias', async () => {
    vi.spyOn(service, 'crearMateria').mockResolvedValue(sampleMateria)
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useCrearMateria(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ codigo: 'M1', nombre: 'Materia 1' })
    })
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'materias'],
    }))
  })
})

// ── useEditarMateria ──────────────────────────────────────────────────────────

describe('useEditarMateria', () => {
  it('calls editarMateria and invalidates materias', async () => {
    vi.spyOn(service, 'editarMateria').mockResolvedValue(sampleMateria)
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useEditarMateria(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ id: 'mat-1', body: { nombre: 'Updated' } })
    })
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'materias'],
    }))
  })
})

// ── useDarBajaMateria ──────────────────────────────────────────────────────────

describe('useDarBajaMateria', () => {
  it('calls darBajaMateria and invalidates', async () => {
    vi.spyOn(service, 'darBajaMateria').mockResolvedValue()
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useDarBajaMateria(), { wrapper })
    await act(async () => { await result.current.mutateAsync('mat-1') })
    expect(service.darBajaMateria).toHaveBeenCalledWith('mat-1')
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'materias'],
    }))
  })
})

// ── useCrearCohorte ───────────────────────────────────────────────────────────

describe('useCrearCohorte', () => {
  it('calls crearCohorte and invalidates cohortes', async () => {
    vi.spyOn(service, 'crearCohorte').mockResolvedValue(sampleCohorte)
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useCrearCohorte(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        carrera_id: 'car-1', nombre: '2026', anio: 2026, vig_desde: '2026-03-01',
      })
    })
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'cohortes'],
    }))
  })
})

// ── useEditarCohorte ──────────────────────────────────────────────────────────

describe('useEditarCohorte', () => {
  it('calls editarCohorte and invalidates cohortes', async () => {
    vi.spyOn(service, 'editarCohorte').mockResolvedValue(sampleCohorte)
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useEditarCohorte(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ id: 'coh-1', body: { nombre: '2026-B' } })
    })
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'cohortes'],
    }))
  })
})

// ── useDarBajaCohorte ──────────────────────────────────────────────────────────

describe('useDarBajaCohorte', () => {
  it('calls darBajaCohorte and invalidates cohortes', async () => {
    vi.spyOn(service, 'darBajaCohorte').mockResolvedValue()
    const { qc, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useDarBajaCohorte(), { wrapper })
    await act(async () => { await result.current.mutateAsync('coh-1') })
    expect(service.darBajaCohorte).toHaveBeenCalledWith('coh-1')
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({
      queryKey: ['admin-estructura', 'cohortes'],
    }))
  })
})
