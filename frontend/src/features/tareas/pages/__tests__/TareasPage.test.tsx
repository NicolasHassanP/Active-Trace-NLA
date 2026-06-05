/**
 * TareasPage render tests — role-gated rendering.
 * Task 3.8 — TDD: RED first.
 * Covers: COORDINADOR sees admin panel, PROFESOR sees only mis-tareas, error state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TareasPage from '../TareasPage'
import * as service from '../../services/tareasService'
import type { TareaRead } from '../../types'

vi.mock('../../services/tareasService')

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

const sampleTarea: TareaRead = {
  id: 'tarea-1',
  tenant_id: 'tenant-1',
  asignado_a: 'user-1',
  asignado_por: 'coord-1',
  descripcion: 'Revisar actas del coloquio',
  estado: 'Pendiente',
  materia_id: null,
  contexto_id: null,
  contexto_tipo: null,
  created_at: '2024-06-01T10:00:00Z',
  updated_at: '2024-06-01T10:00:00Z',
  deleted_at: null,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.listarMias).mockResolvedValue([sampleTarea])
  vi.mocked(service.listarAdmin).mockResolvedValue([sampleTarea])
})

describe('TareasPage — COORDINADOR', () => {
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

  it('renders both admin panel and mis-tareas section', async () => {
    render(<TareasPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('tareas-admin')).toBeInTheDocument())
    expect(screen.getByTestId('tareas-mias')).toBeInTheDocument()
  })

  it('shows "Nueva tarea" button in admin panel', async () => {
    render(<TareasPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('tareas-admin')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /nueva tarea/i })).toBeInTheDocument()
  })
})

describe('TareasPage — PROFESOR', () => {
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

  it('shows only mis-tareas without admin panel', async () => {
    render(<TareasPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('tareas-mias')).toBeInTheDocument())
    expect(screen.queryByTestId('tareas-admin')).not.toBeInTheDocument()
  })

  it('shows mis-tareas list with task data', async () => {
    render(<TareasPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('mis-tareas-list')).toBeInTheDocument())
  })
})

describe('TareasPage — empty mis-tareas', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'prof@test.com', roles: ['TUTOR'], tenantId: 't1' },
      roles: ['TUTOR'],
      tenantId: 't1',
      isAuthenticated: true,
      isInitializing: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    vi.mocked(service.listarMias).mockResolvedValue([])
  })

  it('shows empty state when no tasks assigned', async () => {
    render(<TareasPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('mis-tareas-empty')).toBeInTheDocument())
  })
})

describe('TareasPage — error state', () => {
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
    vi.mocked(service.listarMias).mockRejectedValue({ status: 403, detail: 'Forbidden' })
  })

  it('shows error alert when API call fails', async () => {
    render(<TareasPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
