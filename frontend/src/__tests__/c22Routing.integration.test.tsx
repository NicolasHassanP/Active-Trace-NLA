/**
 * C-22 routing integration tests.
 * Verifies: allowed role renders the page; unauthorized role gets 403 (fail-closed).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProtectedRoute from '@/shared/components/ProtectedRoute'
import * as authHook from '@/features/auth/hooks/useAuth'
import type { Role } from '@/features/auth/types'

vi.mock('@/features/auth/hooks/useAuth')
// Stub the page components to keep test fast
vi.mock('@/features/padron/pages/PadronPage', () => ({ default: () => <div>PadronPage</div> }))
vi.mock('@/features/comunicaciones/pages/ComunicacionesPage', () => ({ default: () => <div>ComunicacionesPage</div> }))

const mockUseAuth = vi.mocked(authHook.useAuth)

function makeAuth(roles: Role[]) {
  mockUseAuth.mockReturnValue({
    user: { id: 'u1', email: 'u@t.com', roles, tenantId: 't1' },
    tenantId: 't1',
    isAuthenticated: true,
    isInitializing: false,
    roles,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

const PadronPage = () => <div>PadronPage</div>
const ComunicacionesPage = () => <div>ComunicacionesPage</div>

function renderRoute(url: string, _roles: Role[], element: React.ReactNode, requiredRoles: Role[]) {
  return render(
    createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(
        MemoryRouter,
        { initialEntries: [url] },
        createElement(
          Routes,
          null,
          // ProtectedRoute uses <Outlet />, so the page must be a child Route
          createElement(
            Route,
            { element: createElement(ProtectedRoute, { requiredRoles }) },
            createElement(Route, { path: url, element }),
          ),
        ),
      ),
    ),
  )
}

beforeEach(() => vi.clearAllMocks())

describe('C-22 routing — fail-closed RBAC', () => {
  it('PROFESOR can access /padron', async () => {
    makeAuth(['PROFESOR'])
    renderRoute('/padron', ['PROFESOR'], <PadronPage />, ['PROFESOR', 'COORDINADOR', 'ADMIN'])
    await waitFor(() => expect(screen.getByText('PadronPage')).toBeInTheDocument())
  })

  it('FINANZAS is blocked from /padron (403)', async () => {
    makeAuth(['FINANZAS'])
    renderRoute('/padron', ['FINANZAS'], <PadronPage />, ['PROFESOR', 'COORDINADOR', 'ADMIN'])
    await waitFor(() => expect(screen.getByText('403')).toBeInTheDocument())
    expect(screen.queryByText('PadronPage')).not.toBeInTheDocument()
  })

  it('TUTOR is blocked from /padron (403) — cargar padrón es PROFESOR/COORD/ADMIN (C-09, KB F1.3)', async () => {
    makeAuth(['TUTOR'])
    renderRoute('/padron', ['TUTOR'], <PadronPage />, ['PROFESOR', 'COORDINADOR', 'ADMIN'])
    await waitFor(() => expect(screen.getByText('403')).toBeInTheDocument())
    expect(screen.queryByText('PadronPage')).not.toBeInTheDocument()
  })

  it('TUTOR can access /comunicaciones', async () => {
    makeAuth(['TUTOR'])
    renderRoute('/comunicaciones', ['TUTOR'], <ComunicacionesPage />, ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'])
    await waitFor(() => expect(screen.getByText('ComunicacionesPage')).toBeInTheDocument())
  })

  it('FINANZAS is blocked from /comunicaciones (403)', async () => {
    makeAuth(['FINANZAS'])
    renderRoute('/comunicaciones', ['FINANZAS'], <ComunicacionesPage />, ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN'])
    await waitFor(() => expect(screen.getByText('403')).toBeInTheDocument())
    expect(screen.queryByText('ComunicacionesPage')).not.toBeInTheDocument()
  })
})
