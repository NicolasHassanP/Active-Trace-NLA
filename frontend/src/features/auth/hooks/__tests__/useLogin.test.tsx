/**
 * Tests for useLogin hook — task 5.3 RED
 *
 * Scenarios:
 * - Success: stores token and hydrates session
 * - 401: exposes error, no token stored
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { type ReactNode } from 'react'
import axios from 'axios'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../AuthProvider'
import { useLogin } from '../useLogin'
import * as tokenStore from '@/shared/services/tokenStore'
import apiClient, { __resetRefreshPromiseForTests } from '@/shared/services/api'
import MockAdapter from 'axios-mock-adapter'

const MOCK_PAYLOAD = { sub: 'u1', tenant_id: 't1', roles: ['ADMIN'], exp: 9999999999, email: 'admin@t.com' }
function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.sig`
}

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('useLogin', () => {
  let mockAxiosPlain: MockAdapter
  let mockApiClient: MockAdapter

  beforeEach(() => {
    // refresh() is coalesced through api.ts's shared refreshPromise, which calls
    // plain axios under the hood → mock 401 (no session) on plain axios.
    mockAxiosPlain = new MockAdapter(axios)
    mockAxiosPlain.onPost('/api/v1/auth/refresh').reply(401)
    // apiClient mock for login endpoint
    mockApiClient = new MockAdapter(apiClient)
    // Isolate the module-level coalesced refresh promise between tests.
    __resetRefreshPromiseForTests()
    tokenStore.clearAll()
  })

  afterEach(() => {
    mockAxiosPlain.restore()
    mockApiClient.restore()
    __resetRefreshPromiseForTests()
    vi.clearAllMocks()
  })

  it('success: stores token and marks session as authenticated', async () => {
    const accessToken = makeJwt(MOCK_PAYLOAD)
    // refresh_token is no longer in the body — it arrives as an httpOnly cookie
    mockApiClient.onPost('/auth/login').reply(200, {
      access_token: accessToken,
      token_type: 'bearer',
    })

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() })

    // Wait for AuthProvider's mount rehydrate (refresh → 401 → clearAll) to settle
    // before logging in. Otherwise its async catch can clear the token AFTER login
    // stores it, racing the assertion below.
    await waitFor(() => expect(result.current.isIdle).toBe(true))

    await act(async () => {
      result.current.mutate({ email: 'admin@t.com', password: 'pass', tenantId: 'tenant-1' })
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(tokenStore.getToken()).toBe(accessToken)
  })

  it('401: exposes error and does not store token', async () => {
    mockApiClient.onPost('/auth/login').reply(401, { detail: 'Invalid credentials' })

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() })

    await act(async () => {
      result.current.mutate({ email: 'bad@t.com', password: 'wrong', tenantId: 'tenant-1' })
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(tokenStore.getToken()).toBeNull()
    expect(result.current.error).toBeTruthy()
  })
})
