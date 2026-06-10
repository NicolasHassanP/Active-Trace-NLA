/**
 * EncuentrosPage render tests — role-gated rendering.
 * Task 5.7 — TDD: RED first, then GREEN.
 * Covers:
 *   - COORDINADOR sees the encuentros panel
 *   - FINANZAS (non-authorized) is blocked
 *   - Empty state when API returns no rows
 *   - Export button present for authorized users
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EncuentrosPage from '../EncuentrosPage'
import * as service from '../../services/encuentrosCoordService'
import type { InstanciaEncuentroRead, GuardiaRead } from '../../types'

vi.mock('../../services/encuentrosCoordService')
vi.mock('@/features/auth/hooks/useAuth', () => ({ useAuth: vi.fn() }))
vi.mock('@/shared/services/downloadFile', () => ({ downloadFile: vi.fn() }))

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

const sampleInstancia: InstanciaEncuentroRead = {
  id: 'inst-1',
  slot_id: null,
  materia_id: 'mat-1',
  fecha: '2024-04-10',
  hora: '18:00:00',
  titulo: 'Clase 1',
  estado: 'Programado',
  meet_url: null,
  video_url: null,
  comentario: '',
}

const sampleGuardia: GuardiaRead = {
  id: 'guardia-1',
  asignacion_id: 'asig-1',
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  dia: 'Lunes',
  horario: '10:00 - 12:00',
  estado: 'Pendiente',
  comentarios: '',
  creada_at: '2024-04-01T10:00:00',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.listarInstancias).mockResolvedValue([sampleInstancia])
  vi.mocked(service.listarGuardias).mockResolvedValue([sampleGuardia])
})

// ---------------------------------------------------------------------------
// COORDINADOR — happy path
// ---------------------------------------------------------------------------

describe('EncuentrosPage — COORDINADOR', () => {
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

  it('renders the encuentros panel for COORDINADOR', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('encuentros-panel')).toBeInTheDocument())
  })

  it('renders instancias table when API returns data', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('instancias-table')).toBeInTheDocument())
    expect(screen.getByText('Clase 1')).toBeInTheDocument()
  })

  it('renders guardias table when API returns data', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('guardias-table')).toBeInTheDocument())
  })

  it('shows export button for guardias', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('encuentros-panel')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /exportar guardias/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// ADMIN — also authorized
// ---------------------------------------------------------------------------

describe('EncuentrosPage — ADMIN', () => {
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

  it('renders the encuentros panel for ADMIN', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('encuentros-panel')).toBeInTheDocument())
  })
})

// ---------------------------------------------------------------------------
// FINANZAS — non-authorized
// ---------------------------------------------------------------------------

describe('EncuentrosPage — FINANZAS (non-authorized)', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u3', email: 'fin@test.com', roles: ['FINANZAS'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['FINANZAS'],
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

  it('does not render the encuentros panel for FINANZAS', () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    expect(screen.queryByTestId('encuentros-panel')).not.toBeInTheDocument()
  })

  it('shows access-denied message for FINANZAS', () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('encuentros-access-denied')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

describe('EncuentrosPage — empty states', () => {
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
    vi.mocked(service.listarInstancias).mockResolvedValue([])
    vi.mocked(service.listarGuardias).mockResolvedValue([])
  })

  it('shows empty state for instancias when API returns no rows', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('instancias-empty')).toBeInTheDocument())
  })

  it('shows empty state for guardias when API returns no rows', async () => {
    render(<EncuentrosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('guardias-empty')).toBeInTheDocument())
  })
})
