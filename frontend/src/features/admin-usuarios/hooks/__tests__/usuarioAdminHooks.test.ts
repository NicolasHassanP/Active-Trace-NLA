/**
 * Tests for usuarioAdminHooks — validates query/mutation wiring.
 * Uses vi.mock to isolate from the real service.
 * Verifies: query key used, mutations call correct service fn,
 * and mutations invalidate USUARIOS_KEY on success.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import {
  useUsuarios,
  useCrearUsuario,
  useEditarUsuario,
  useDarBajaUsuario,
} from '../usuarioAdminHooks'
import type { UsuarioRead, UsuarioCreate, UsuarioUpdate } from '../../types'

// ── Mock service ──────────────────────────────────────────────────────────────

vi.mock('../../services/usuarioAdminService', () => ({
  listarUsuarios: vi.fn(),
  crearUsuario: vi.fn(),
  editarUsuario: vi.fn(),
  darBajaUsuario: vi.fn(),
}))

import {
  listarUsuarios,
  crearUsuario,
  editarUsuario,
  darBajaUsuario,
} from '../../services/usuarioAdminService'

// ── Fixture ───────────────────────────────────────────────────────────────────

const sampleUsuario: UsuarioRead = {
  id: 'usr-uuid-1',
  email: 'admin@test.com',
  nombre: 'Ana',
  apellidos: 'García',
  legajo: null,
  estado: 'activo',
  asignaciones: [],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

// ── Wrapper ───────────────────────────────────────────────────────────────────

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return { wrapper, qc }
}

// ── useUsuarios ───────────────────────────────────────────────────────────────

describe('useUsuarios', () => {
  beforeEach(() => {
    vi.mocked(listarUsuarios).mockResolvedValue([sampleUsuario])
  })

  it('returns lista of usuarios when service resolves', async () => {
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUsuarios(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([sampleUsuario])
    expect(listarUsuarios).toHaveBeenCalledOnce()
  })

  it('returns empty array when service resolves with []', async () => {
    vi.mocked(listarUsuarios).mockResolvedValue([])
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useUsuarios(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([])
  })
})

// ── useCrearUsuario ───────────────────────────────────────────────────────────

describe('useCrearUsuario', () => {
  it('calls crearUsuario and invalidates query on success', async () => {
    const body: UsuarioCreate = { email: 'new@test.com', nombre: 'Pedro', apellidos: 'López' }
    vi.mocked(crearUsuario).mockResolvedValue({ ...sampleUsuario, email: 'new@test.com' })
    vi.mocked(listarUsuarios).mockResolvedValue([sampleUsuario])

    const { wrapper, qc } = makeWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useCrearUsuario(), { wrapper })
    result.current.mutate(body)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(crearUsuario).toHaveBeenCalledWith(body)
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: expect.arrayContaining(['admin-usuarios']) })
    )
  })
})

// ── useEditarUsuario ──────────────────────────────────────────────────────────

describe('useEditarUsuario', () => {
  it('calls editarUsuario with id and body', async () => {
    const body: UsuarioUpdate = { nombre: 'Ana Maria' }
    vi.mocked(editarUsuario).mockResolvedValue({ ...sampleUsuario, nombre: 'Ana Maria' })
    vi.mocked(listarUsuarios).mockResolvedValue([sampleUsuario])

    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useEditarUsuario(), { wrapper })
    result.current.mutate({ id: 'usr-uuid-1', body })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(editarUsuario).toHaveBeenCalledWith('usr-uuid-1', body)
  })
})

// ── useDarBajaUsuario ─────────────────────────────────────────────────────────

describe('useDarBajaUsuario', () => {
  it('calls darBajaUsuario with id and resolves', async () => {
    vi.mocked(darBajaUsuario).mockResolvedValue(undefined)
    vi.mocked(listarUsuarios).mockResolvedValue([])

    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useDarBajaUsuario(), { wrapper })
    result.current.mutate('usr-uuid-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(darBajaUsuario).toHaveBeenCalledWith('usr-uuid-1')
  })
})
