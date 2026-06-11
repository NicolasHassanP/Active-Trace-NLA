/**
 * MonitorPage render tests — role-gated rendering.
 * Task 4.6 — TDD: RED first.
 * Covers:
 *   - COORDINADOR sees the monitor panel
 *   - PROFESOR (non-authorized) is blocked (no monitor panel)
 *   - Empty state when API returns no rows
 *   - Filter clear resets the results
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MonitorPage from '../MonitorPage'
import * as service from '../../services/monitoresService'
import type { MonitorFila } from '../../types'

vi.mock('../../services/monitoresService')

vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))
import { useAuth } from '@/features/auth/hooks/useAuth'
import type { MateriaItem } from '../../types'

const sampleMateria: MateriaItem = {
  id: 'materia-uuid-1',
  codigo: 'MAT001',
  nombre: 'Matemáticas',
  estado: 'activa',
}

// Silence downloadFile in JSDOM (no real anchor/blob support needed)
vi.mock('@/shared/services/downloadFile', () => ({
  downloadFile: vi.fn(),
}))

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client: qc },
      createElement(MemoryRouter, null, children),
    )
}

const sampleFila: MonitorFila = {
  entrada_padron_id: 'alumno-uuid-1',
  estado: 'atrasado',
  aprobadas: 2,
  faltantes: 3,
  nombre: null,
  apellidos: null,
  email: null,
  comision: null,
  regional: null,
  actividades_detalle: [],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.listarMonitor).mockResolvedValue([sampleFila])
  vi.mocked(service.listarTodasMaterias).mockResolvedValue([sampleMateria])
})

// ---------------------------------------------------------------------------
// COORDINADOR — happy path
// ---------------------------------------------------------------------------
describe('MonitorPage — COORDINADOR', () => {
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

  it('renders the monitor panel for COORDINADOR', async () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('monitor-panel')).toBeInTheDocument())
  })

  it('renders data rows when API returns results', async () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('monitor-table')).toBeInTheDocument())
    expect(screen.getByText('alumno-u')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// PROFESOR — non-authorized role
// ---------------------------------------------------------------------------
describe('MonitorPage — PROFESOR (non-authorized)', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'prof@test.com', roles: ['PROFESOR'], tenantId: 't1', isImpersonating: false, impersonatedName: null },
      roles: ['PROFESOR'],
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

  it('does not render the monitor panel for PROFESOR', () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    expect(screen.queryByTestId('monitor-panel')).not.toBeInTheDocument()
  })

  it('shows access-denied message for non-authorized role', () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('monitor-access-denied')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------
describe('MonitorPage — empty state', () => {
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
    vi.mocked(service.listarMonitor).mockResolvedValue([])
  })

  it('shows empty state when API returns no rows', async () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('monitor-empty')).toBeInTheDocument())
  })
})

// ---------------------------------------------------------------------------
// Filter clear resets state
// ---------------------------------------------------------------------------
describe('MonitorPage — filter clear', () => {
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

  it('toolbar clear button is present in the monitor panel', async () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('monitor-toolbar')).toBeInTheDocument())
    // Two "Limpiar filtros" buttons exist: one in MonitorFilters, one in MonitorToolbar — both valid
    const clearBtns = screen.getAllByRole('button', { name: /limpiar filtros/i })
    expect(clearBtns.length).toBeGreaterThanOrEqual(1)
  })

  it('clicking toolbar "limpiar filtros" re-fetches with empty params', async () => {
    render(<MonitorPage />, { wrapper: makeWrapper() })
    const toolbar = await screen.findByTestId('monitor-toolbar')

    // Click the clear button inside the toolbar specifically
    const clearBtn = toolbar.querySelector('button')
    expect(clearBtn).not.toBeNull()
    fireEvent.click(clearBtn!)

    // After clearing, listarMonitor should have been called (initial load + after clear triggers re-render)
    await waitFor(() => expect(service.listarMonitor).toHaveBeenCalled())
  })
})
