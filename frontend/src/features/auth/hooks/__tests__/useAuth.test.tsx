/**
 * Tests for useAuth hook — tasks 4.1, 4.3 RED
 *
 * Scenarios:
 * - Without session: isAuthenticated=false, user=null, roles=[]
 * - With session: reflects backend identity
 * - Rehydration on mount: success → hydrates AuthUser; failure → unauthenticated
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { AuthProvider } from '../AuthProvider'
import { useAuth } from '../useAuth'
import * as tokenStore from '@/shared/services/tokenStore'

// A valid JWT payload for test: { sub: 'user-1', tenant_id: 'tenant-1', roles: ['ADMIN'], exp: 9999999999, email: 'admin@test.com' }
const MOCK_JWT_PAYLOAD = { sub: 'user-1', tenant_id: 'tenant-1', roles: ['ADMIN'], exp: 9999999999, email: 'admin@test.com' }
function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).replace(/=/g, '')
  const body = btoa(JSON.stringify(payload)).replace(/=/g, '')
  return `${header}.${body}.fake-signature`
}

const MOCK_ACCESS_TOKEN = makeJwt(MOCK_JWT_PAYLOAD)

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}

describe('useAuth — no session', () => {
  let mockAxios: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // authService.refresh() uses plain axios with /api/v1/auth/refresh
    mockAxios = new MockAdapter(axios)
    // apiClient is mocked to prevent any stray calls
    mockApiClient = new MockAdapter(apiClient)
    tokenStore.clearAll()
    // Refresh fails → no session
    mockAxios.onPost('/api/v1/auth/refresh').reply(401)
  })

  afterEach(() => {
    mockAxios.restore()
    mockApiClient.restore()
    vi.clearAllMocks()
  })

  it('reports isAuthenticated=false, user=null, roles=[] when no session', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isInitializing).toBe(false))

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(result.current.roles).toEqual([])
  })
})

describe('useAuth — with session (rehydration success)', () => {
  let mockAxios: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // authService.refresh() uses plain axios with /api/v1/auth/refresh
    mockAxios = new MockAdapter(axios)
    mockApiClient = new MockAdapter(apiClient)
    tokenStore.clearAll()
    // Refresh token now travels as httpOnly cookie — no in-memory store needed
    // Refresh succeeds — only access_token in body
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: MOCK_ACCESS_TOKEN,
      token_type: 'bearer',
    })
  })

  afterEach(() => {
    mockAxios.restore()
    mockApiClient.restore()
    vi.clearAllMocks()
  })

  it('reflects backend identity after successful rehydration', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isInitializing).toBe(false))

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).not.toBeNull()
    expect(result.current.user?.id).toBe('user-1')
    expect(result.current.user?.tenantId).toBe('tenant-1')
    expect(result.current.roles).toContain('ADMIN')
    expect(result.current.tenantId).toBe('tenant-1')
  })

  it('isInitializing is true before rehydration resolves and false after', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() })

    // Initially: isInitializing=true (rehydration in progress)
    expect(result.current.isInitializing).toBe(true)

    await waitFor(() => expect(result.current.isInitializing).toBe(false))
  })
})
