/**
 * ColoquiosPage render tests — role-gated rendering.
 * Task 6.11 — TDD: RED first, then GREEN.
 * Covers:
 *   - COORDINADOR sees the coloquios panel with metrics and convocatorias
 *   - TUTOR (non-authorized) is blocked
 *   - ADMIN is authorized
 *   - Empty convocatorias state
 *   - Metrics panel rendered with correct fields
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ColoquiosPage from '../ColoquiosPage'
import * as service from '../../services/coloquiosService'
import type {
  MetricasRead,
  ConvocatoriaMetricasRead,
  AgendaItemRead,
} from '../../types'

vi.mock('../../services/coloquiosService')
vi.mock('@/features/auth/hooks/useAuth', () => ({ useAuth: vi.fn() }))

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

const sampleMetricas: MetricasRead = {
  convocatorias_activas: 3,
  alumnos_cargados: 100,
  reservas_activas: 20,
  notas_registradas: 15,
}

const sampleConvocatoria: ConvocatoriaMetricasRead = {
  id: 'eval-1',
  materia_id: 'mat-1',
  cohorte_id: 'coh-1',
  tipo: 'Coloquio',
  instancia: 'Primera',
  cerrada: false,
  convocados: 30,
  reservas_activas: 10,
  cupos_libres: 5,
}

const sampleAgenda: AgendaItemRead[] = []

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.metricas).mockResolvedValue(sampleMetricas)
  vi.mocked(service.listarConvocatorias).mockResolvedValue([sampleConvocatoria])
  vi.mocked(service.agenda).mockResolvedValue(sampleAgenda)
})

// ---------------------------------------------------------------------------
// COORDINADOR — happy path
// ---------------------------------------------------------------------------

describe('ColoquiosPage — COORDINADOR', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['COORDINADOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
  })

  it('renders the coloquios panel for COORDINADOR', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('coloquios-panel')).toBeInTheDocument())
  })

  it('renders the metrics panel', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('metricas-panel')).toBeInTheDocument())
  })

  it('renders convocatorias table when data is available', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('convocatorias-table')).toBeInTheDocument())
    expect(screen.getByText('Primera')).toBeInTheDocument()
  })

  it('shows create convocatoria button', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('coloquios-panel')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /nueva convocatoria/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// ADMIN — also authorized
// ---------------------------------------------------------------------------

describe('ColoquiosPage — ADMIN', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'admin@test.com', roles: ['ADMIN'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['ADMIN'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
  })

  it('renders the coloquios panel for ADMIN', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('coloquios-panel')).toBeInTheDocument())
  })
})

// ---------------------------------------------------------------------------
// TUTOR — non-authorized
// ---------------------------------------------------------------------------

describe('ColoquiosPage — TUTOR (non-authorized)', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u3', email: 'tutor@test.com', roles: ['TUTOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['TUTOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
  })

  it('does not render the coloquios panel for TUTOR', () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    expect(screen.queryByTestId('coloquios-panel')).not.toBeInTheDocument()
  })

  it('shows access-denied message for TUTOR', () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('coloquios-access-denied')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Empty convocatorias state
// ---------------------------------------------------------------------------

describe('ColoquiosPage — empty convocatorias', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['COORDINADOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
    vi.mocked(service.listarConvocatorias).mockResolvedValue([])
  })

  it('shows empty state when no convocatorias', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('convocatorias-empty')).toBeInTheDocument())
  })
})

// ---------------------------------------------------------------------------
// Metrics values rendered
// ---------------------------------------------------------------------------

describe('ColoquiosPage — metrics values', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['COORDINADOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
      isImpersonating: false,
      impersonatedName: null,
      impersonarUsuario: vi.fn(),
      finalizarImpersonacion: vi.fn(),
    })
  })

  it('displays metric values from API response', async () => {
    render(<ColoquiosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('metricas-panel')).toBeInTheDocument())
    expect(screen.getByText('3')).toBeInTheDocument()   // convocatorias_activas
    expect(screen.getByText('100')).toBeInTheDocument() // alumnos_cargados
  })
})
