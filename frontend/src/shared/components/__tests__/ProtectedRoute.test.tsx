/**
 * Tests for ProtectedRoute — tasks 7.1, 7.3 RED
 *
 * Scenarios:
 * - Without session → redirects to /login preserving destination
 * - With session → renders children
 * - isInitializing → shows loading state (no redirect)
 * - Role check: required role present → renders; absent → shows 403
 * - Multiple roles accepted: COORDINADOR | ADMIN → ADMIN gets in
 * - Fail-closed: no roles match → 403
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient, { __resetRefreshPromiseForTests } from '@/shared/services/api'
import { AuthProvider } from '@/features/auth/hooks/AuthProvider'
import ProtectedRoute from '../ProtectedRoute'
import * as tokenStore from '@/shared/services/tokenStore'
import type { Role } from '@/features/auth/types'

function makeJwt(payload: Record<string, unknown>): string {
  return `${btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))}.${btoa(JSON.stringify(payload))}.sig`
}

const ADMIN_TOKEN = makeJwt({ sub: 'u1', tenant_id: 't1', roles: ['ADMIN'], exp: 9999999999, email: 'a@t.com' })
const PROFESOR_TOKEN = makeJwt({ sub: 'u2', tenant_id: 't1', roles: ['PROFESOR'], exp: 9999999999, email: 'p@t.com' })

function createWrapper(initialPath: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ProtectedRoute — authentication guard', () => {
  let mockAxios: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // refresh() is coalesced through api.ts's shared refreshPromise, which calls
    // plain axios under the hood → mock the full path on plain axios.
    mockAxios = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    // Clear the module-level coalesced refresh promise so a hung/settled refresh
    // from a prior test cannot leak into this one (e.g. the never-resolving
    // "shows loading state" mock).
    __resetRefreshPromiseForTests()
    tokenStore.clearAll()
  })

  afterEach(() => {
    mockAxios.restore()
    mockApiClient.restore()
    __resetRefreshPromiseForTests()
  })

  it('redirects unauthenticated user to /login', async () => {
    mockAxios.onPost('/api/v1/auth/refresh').reply(401)
    const Wrapper = createWrapper('/dashboard')

    render(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
  })

  it('renders content when user is authenticated', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: ADMIN_TOKEN,
      token_type: 'bearer',
    })
    const Wrapper = createWrapper('/dashboard')

    render(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Protected Content</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })
  })

  it('shows loading state while isInitializing', () => {
    // Never resolves during this test (we just check initial render)
    mockAxios.onPost('/api/v1/auth/refresh').reply(() => new Promise(() => undefined))
    const Wrapper = createWrapper('/dashboard')

    render(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    // Should show loading, not login or content
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('ProtectedRoute — role authorization', () => {
  let mockAxios: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // refresh() is coalesced through api.ts's shared refreshPromise, which calls
    // plain axios under the hood → mock the full path on plain axios.
    mockAxios = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    // Clear the module-level coalesced refresh promise so a hung/settled refresh
    // from a prior test cannot leak into this one (e.g. the never-resolving
    // "shows loading state" mock).
    __resetRefreshPromiseForTests()
    tokenStore.clearAll()
  })

  afterEach(() => {
    mockAxios.restore()
    mockApiClient.restore()
    __resetRefreshPromiseForTests()
  })

  it('user with required role accesses the route', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: ADMIN_TOKEN,
      token_type: 'bearer',
    })
    const Wrapper = createWrapper('/admin')

    render(
      <Routes>
        <Route element={<ProtectedRoute requiredRoles={['ADMIN'] as Role[]} />}>
          <Route path="/admin" element={<div>Admin Area</div>} />
        </Route>
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText('Admin Area')).toBeInTheDocument()
    })
  })

  it('user without required role sees 403', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: PROFESOR_TOKEN,
      token_type: 'bearer',
    })
    const Wrapper = createWrapper('/finanzas')

    render(
      <Routes>
        <Route element={<ProtectedRoute requiredRoles={['FINANZAS'] as Role[]} />}>
          <Route path="/finanzas" element={<div>Finanzas Area</div>} />
        </Route>
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText(/403/i)).toBeInTheDocument()
      expect(screen.queryByText('Finanzas Area')).not.toBeInTheDocument()
    })
  })

  it('multiple accepted roles — ADMIN gets in when COORDINADOR|ADMIN required', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: ADMIN_TOKEN,
      token_type: 'bearer',
    })
    const Wrapper = createWrapper('/coord')

    render(
      <Routes>
        <Route element={<ProtectedRoute requiredRoles={['COORDINADOR', 'ADMIN'] as Role[]} />}>
          <Route path="/coord" element={<div>Coord Area</div>} />
        </Route>
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText('Coord Area')).toBeInTheDocument()
    })
  })
})
