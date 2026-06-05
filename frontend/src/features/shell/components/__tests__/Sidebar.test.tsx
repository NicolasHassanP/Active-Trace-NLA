/**
 * Tests for Sidebar component — task 8.3 RED
 *
 * Scenarios:
 * - Renders items for the current user's roles
 * - Does NOT render items for other roles
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { AuthProvider } from '@/features/auth/hooks/AuthProvider'
import Sidebar from '../Sidebar'
import * as tokenStore from '@/shared/services/tokenStore'

function makeJwt(payload: Record<string, unknown>): string {
  return `${btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))}.${btoa(JSON.stringify(payload))}.sig`
}

const FINANZAS_TOKEN = makeJwt({ sub: 'u1', tenant_id: 't1', roles: ['FINANZAS'], exp: 9999999999 })
const ADMIN_TOKEN = makeJwt({ sub: 'u2', tenant_id: 't1', roles: ['ADMIN'], exp: 9999999999 })

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Sidebar', () => {
  let mockAxios: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // authService.refresh() uses plain axios → mock the full path
    mockAxios = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    tokenStore.clearAll()
  })

  afterEach(() => {
    mockAxios.restore()
    mockApiClient.restore()
  })

  it('renders nav items corresponding to FINANZAS role', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: FINANZAS_TOKEN,
      token_type: 'bearer',
    })

    render(<Sidebar />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Liquidaciones')).toBeInTheDocument()
    })
    // Should NOT see Admin-only items
    expect(screen.queryByText('Usuarios')).not.toBeInTheDocument()
    expect(screen.queryByText('Auditoría')).not.toBeInTheDocument()
  })

  it('ADMIN sees admin items', async () => {
    // Refresh token travels as httpOnly cookie — no in-memory store needed
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: ADMIN_TOKEN,
      token_type: 'bearer',
    })

    render(<Sidebar />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Usuarios')).toBeInTheDocument()
      expect(screen.getByText('Auditoría')).toBeInTheDocument()
    })
  })

  it('shows nothing (returns null) when session is not yet loaded (isInitializing)', () => {
    mockAxios.onPost('/api/v1/auth/refresh').reply(() => new Promise(() => undefined))

    render(<Sidebar />, { wrapper: createWrapper() })

    // No nav element while loading
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })
})
