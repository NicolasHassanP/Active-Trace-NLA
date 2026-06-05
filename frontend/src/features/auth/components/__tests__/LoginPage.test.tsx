/**
 * Tests for LoginPage — tasks 6.1, 6.3 RED
 *
 * Scenarios:
 * - Renders the form with email and password fields
 * - Zod validation error → does not fire request
 * - Valid submit → invokes useLogin (mutation)
 * - 401 error → shows generic error message, does not navigate
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { AuthProvider } from '../../hooks/AuthProvider'
import LoginPage from '../LoginPage'
import * as tokenStore from '@/shared/services/tokenStore'

const MOCK_PAYLOAD = { sub: 'u1', tenant_id: 't1', roles: ['ADMIN'], exp: 9999999999, email: 'admin@t.com' }
function makeJwt(p: Record<string, unknown>): string {
  return `${btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))}.${btoa(JSON.stringify(p))}.sig`
}

function createWrapper(initialPath = '/login') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={children} />
            <Route path="/dashboard" element={<div>Dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('LoginPage', () => {
  let mockAxiosPlain: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // authService.refresh() uses plain axios with /api/v1/auth/refresh
    mockAxiosPlain = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    tokenStore.clearAll()
    // Prevent rehydration from succeeding
    mockAxiosPlain.onPost('/api/v1/auth/refresh').reply(401)
  })

  afterEach(() => {
    mockAxiosPlain.restore()
    mockApiClient.restore()
    vi.clearAllMocks()
  })

  it('renders the login form', async () => {
    const Wrapper = createWrapper()
    render(<LoginPage />, { wrapper: Wrapper })

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
  })

  it('shows validation error for invalid email without firing request', async () => {
    const Wrapper = createWrapper()
    render(<LoginPage />, { wrapper: Wrapper })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/contraseña/i), 'secret')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByText(/email inválido/i)).toBeInTheDocument()
    })

    // No login call should have been made
    expect(mockApiClient.history.post.filter(r => r.url?.includes('/auth/login'))).toHaveLength(0)
  })

  it('submits valid credentials and calls login endpoint', async () => {
    const accessToken = makeJwt(MOCK_PAYLOAD)
    // refresh_token is no longer in the body — it arrives as an httpOnly cookie
    mockApiClient.onPost('/auth/login').reply(200, {
      access_token: accessToken,
      token_type: 'bearer',
    })

    const Wrapper = createWrapper()
    render(<LoginPage />, { wrapper: Wrapper })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'admin@t.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'password123')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(mockApiClient.history.post.filter(r => r.url?.includes('login'))).toHaveLength(1)
    })
  })

  it('shows generic error message on 401 and stays on login page', async () => {
    mockApiClient.onPost('/auth/login').reply(401, { detail: 'Invalid credentials' })

    const Wrapper = createWrapper()
    render(<LoginPage />, { wrapper: Wrapper })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByText(/email o contraseña incorrectos/i)).toBeInTheDocument()
    })

    // Still on login page
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
  })
})
