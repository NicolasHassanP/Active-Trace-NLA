/**
 * AvisosPage render tests — role-gated rendering.
 * Task 2.8 — TDD: RED first, then GREEN.
 * COORDINADOR sees management actions.
 * TUTOR sees only bandeja (no management).
 * Any authenticated user sees the aviso feed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AvisosPage from '../AvisosPage'
import * as service from '../../services/avisosService'
import type { AvisoRead } from '../../types'

vi.mock('../../services/avisosService')
vi.mock('@/features/auth/hooks/useAuth', () => ({ useAuth: vi.fn() }))
import { useAuth } from '@/features/auth/hooks/useAuth'

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, createElement(MemoryRouter, null, children))
}

const sampleAviso: AvisoRead = {
  id: 'av-1', tenant_id: 'ten-1', alcance: 'Global',
  materia_id: null, cohorte_id: null, rol_destino: null,
  severidad: 'Info', titulo: 'Aviso de prueba', cuerpo: 'Cuerpo',
  inicio_en: '2024-03-01T00:00:00', fin_en: '2024-04-01T00:00:00',
  orden: 100, activo: true, requiere_ack: false, ack_count: 0,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.listarFeed).mockResolvedValue([sampleAviso])
  vi.mocked(service.listarPendientes).mockResolvedValue([])
  vi.mocked(service.listarGestion).mockResolvedValue([sampleAviso])
})

describe('AvisosPage — COORDINADOR', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u1', email: 'coord@test.com', roles: ['COORDINADOR'], tenantId: 't1' },
      roles: ['COORDINADOR'], tenantId: 't1', isAuthenticated: true, isInitializing: false,
      login: vi.fn(), logout: vi.fn(),
    })
  })

  it('renders the management panel', async () => {
    render(<AvisosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('avisos-gestion')).toBeInTheDocument())
  })

  it('renders the bandeja section', async () => {
    render(<AvisosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('avisos-bandeja')).toBeInTheDocument())
  })
})

describe('AvisosPage — TUTOR', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'tutor@test.com', roles: ['TUTOR'], tenantId: 't1' },
      roles: ['TUTOR'], tenantId: 't1', isAuthenticated: true, isInitializing: false,
      login: vi.fn(), logout: vi.fn(),
    })
  })

  it('renders the bandeja section without management actions', async () => {
    render(<AvisosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('avisos-bandeja')).toBeInTheDocument())
    expect(screen.queryByTestId('avisos-gestion')).not.toBeInTheDocument()
  })

  it('shows aviso titles from the feed', async () => {
    render(<AvisosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByText('Aviso de prueba')).toBeInTheDocument())
  })
})

describe('AvisosPage — empty feed', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'u2', email: 'tutor@test.com', roles: ['TUTOR'], tenantId: 't1' },
      roles: ['TUTOR'], tenantId: 't1', isAuthenticated: true, isInitializing: false,
      login: vi.fn(), logout: vi.fn(),
    })
    vi.mocked(service.listarFeed).mockResolvedValue([])
  })

  it('shows empty bandeja message', async () => {
    render(<AvisosPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('avisos-empty')).toBeInTheDocument())
  })
})
