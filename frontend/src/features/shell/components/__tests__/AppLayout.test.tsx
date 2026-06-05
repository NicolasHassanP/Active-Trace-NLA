/**
 * Tests for AppLayout — task 9.1 RED
 *
 * Scenarios:
 * - Shows sidebar and topbar when authenticated
 * - Topbar shows user identity and logout action
 * - Only content area changes between routes (sidebar/topbar persist)
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { AuthProvider } from '@/features/auth/hooks/AuthProvider'
import AppLayout from '../AppLayout'
import * as tokenStore from '@/shared/services/tokenStore'

function makeJwt(payload: Record<string, unknown>): string {
  return `${btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))}.${btoa(JSON.stringify(payload))}.sig`
}

const ADMIN_TOKEN = makeJwt({ sub: 'u1', tenant_id: 't1', roles: ['ADMIN'], exp: 9999999999, email: 'admin@test.com' })

function createWrapper(initialPath = '/dashboard') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AppLayout', () => {
  let mockAxios: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // authService.refresh() uses plain axios → mock the full path
    mockAxios = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    tokenStore.clearAll()
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: ADMIN_TOKEN,
      token_type: 'bearer',
    })
  })

  afterEach(() => {
    mockAxios.restore()
    mockApiClient.restore()
  })

  it('shows topbar (header) when authenticated', async () => {
    const Wrapper = createWrapper()

    render(
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<div>Dashboard Content</div>} />
        </Route>
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByRole('banner')).toBeInTheDocument() // topbar = header
      expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
    })
  })

  it('topbar shows user email and logout button', async () => {
    const Wrapper = createWrapper()

    render(
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Route>
        <Route path="/login" element={<div>Login</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByText('admin@test.com')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cerrar sesión/i })).toBeInTheDocument()
    })
  })

  it('logout button triggers logout and redirects to /login', async () => {
    mockApiClient.onPost('/auth/logout').reply(200, { message: 'Logged out successfully' })

    const Wrapper = createWrapper()

    render(
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>,
      { wrapper: Wrapper },
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cerrar sesión/i })).toBeInTheDocument()
    })

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /cerrar sesión/i }))

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
  })
})
