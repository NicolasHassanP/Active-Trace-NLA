/**
 * Integration test for the auth flow — task 10.1
 *
 * Flow: login → access protected route → logout → /login
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { AuthProvider } from '@/features/auth/hooks/AuthProvider'
import LoginPage from '@/features/auth/components/LoginPage'
import ProtectedRoute from '@/shared/components/ProtectedRoute'
import AppLayout from '@/features/shell/components/AppLayout'
import * as tokenStore from '@/shared/services/tokenStore'

function makeJwt(payload: Record<string, unknown>): string {
  return `${btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))}.${btoa(JSON.stringify(payload))}.sig`
}

const MOCK_PAYLOAD = { sub: 'u1', tenant_id: 't1', roles: ['ADMIN'], exp: 9999999999, email: 'user@test.com' }
const ACCESS_TOKEN = makeJwt(MOCK_PAYLOAD)

function createIntegrationWrapper(initialPath: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Auth flow integration', () => {
  let mockAxiosPlain: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // authService.refresh() uses plain axios → mock the full path
    mockAxiosPlain = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    tokenStore.clearAll()
  })

  afterEach(() => {
    mockAxiosPlain.restore()
    mockApiClient.restore()
  })

  it('unauthenticated user → redirected to login → stays at login', async () => {
    // No session — refresh fails
    mockAxiosPlain.onPost('/api/v1/auth/refresh').reply(401)
    const Wrapper = createIntegrationWrapper('/dashboard')

    render(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<div>Protected Dashboard</div>} />
          </Route>
        </Route>
      </Routes>,
      { wrapper: Wrapper },
    )

    // Redirected to login
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
    })
    expect(screen.queryByText('Protected Dashboard')).not.toBeInTheDocument()
  })

  it('login → access protected route → logout → back to login', async () => {
    // No session initially
    mockAxiosPlain.onPost('/api/v1/auth/refresh').replyOnce(401)

    const Wrapper = createIntegrationWrapper('/dashboard')

    render(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<div>Protected Dashboard</div>} />
          </Route>
        </Route>
      </Routes>,
      { wrapper: Wrapper },
    )

    // Should redirect to login
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
    })

    // Login — refresh_token is no longer in the body (httpOnly cookie)
    mockApiClient.onPost('/auth/login').reply(200, {
      access_token: ACCESS_TOKEN,
      token_type: 'bearer',
    })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'user@test.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'pass123')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    // Now authenticated → should see protected route
    await waitFor(() => {
      expect(screen.getByText('Protected Dashboard')).toBeInTheDocument()
    })

    // Logout
    mockApiClient.onPost('/auth/logout').reply(200, { message: 'OK' })
    await user.click(screen.getByRole('button', { name: /cerrar sesión/i }))

    // Back at login
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
    })
  })

  it('authenticated user with valid refresh token → sees dashboard without login', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxiosPlain.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: ACCESS_TOKEN,
      token_type: 'bearer',
    })

    const Wrapper = createIntegrationWrapper('/dashboard')

    render(
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<div>Dashboard</div>} />
          </Route>
        </Route>
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })
})
