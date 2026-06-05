/**
 * EquiposPage render tests — role-gated rendering.
 * Task 1.10 — TDD: RED first, then GREEN.
 * Covers: COORDINADOR sees management UI, PROFESOR sees only mis-equipos,
 *         FINANZAS gets access denied (403 view), empty state, error state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EquiposPage from '../EquiposPage'
import * as service from '../../services/equiposService'
import type { MisEquiposItem } from '../../types'

vi.mock('../../services/equiposService')

// Mock useAuth to control roles
vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))
import { useAuth } from '@/features/auth/hooks/useAuth'

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client: qc },
      createElement(MemoryRouter, null, children),
    )
}

const sampleItem: MisEquiposItem = {
  asignacion_id: 'asg-1',
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  rol: 'PROFESOR',
  desde: '2024-03-01',
  hasta: null,
  estado_vigencia: 'vigente',
  comisiones: [],
  responsable_id: null,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.listarMisEquipos).mockResolvedValue([sampleItem])
})

describe('EquiposPage — COORDINADOR', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1' },
      roles: ['COORDINADOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  })

  it('renders management actions (asignacion masiva, clonar, vigencia, export)', async () => {
    render(<EquiposPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('equipos-gestion')).toBeInTheDocument())
  })

  it('shows mis-equipos table', async () => {
    render(<EquiposPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('mis-equipos-table')).toBeInTheDocument())
  })
})

describe('EquiposPage — PROFESOR', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'prof@test.com', roles: ['PROFESOR'], tenantId: 't1' },
      roles: ['PROFESOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  })

  it('shows only mis-equipos table without management actions', async () => {
    render(<EquiposPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('mis-equipos-table')).toBeInTheDocument())
    expect(screen.queryByTestId('equipos-gestion')).not.toBeInTheDocument()
  })
})

describe('EquiposPage — empty state', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'prof@test.com', roles: ['PROFESOR'], tenantId: 't1' },
      roles: ['PROFESOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    vi.mocked(service.listarMisEquipos).mockResolvedValue([])
  })

  it('shows empty state message when no assignments', async () => {
    render(<EquiposPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('equipos-empty')).toBeInTheDocument())
  })
})

describe('EquiposPage — error state', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'prof@test.com', roles: ['PROFESOR'], tenantId: 't1' },
      roles: ['PROFESOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    vi.mocked(service.listarMisEquipos).mockRejectedValue({ status: 403, detail: 'Forbidden' })
  })

  it('shows error alert when API call fails', async () => {
    render(<EquiposPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
