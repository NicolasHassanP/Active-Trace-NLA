/**
 * Tests for the Axios response interceptor — tasks 3.3, 3.4, 3.5 RED
 *
 * Scenarios tested:
 * - 401 with valid refresh → refreshes, retries original request, resolves
 * - 401 with invalid refresh → clears session, signals logout
 * - Concurrent 401s → single refresh fired, all requests retried
 * - Already-retried request getting 401 → no second refresh, logout forced
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import apiClient, { registerLogoutCallback } from '../api'
import * as tokenStore from '../tokenStore'

describe('api response interceptor — 401 handling', () => {
  let mockClient: MockAdapter
  let mockAxios: MockAdapter

  const setupLogoutSpy = () => {
    const logoutSpy = vi.fn()
    registerLogoutCallback(logoutSpy)
    return logoutSpy
  }

  beforeEach(() => {
    mockClient = new MockAdapter(apiClient)
    mockAxios = new MockAdapter(axios)
    tokenStore.clearAll()
    tokenStore.setToken('expired-access-token')
    // Refresh token now travels as an httpOnly cookie — no in-memory store needed
    registerLogoutCallback(() => undefined)
  })

  afterEach(() => {
    mockClient.restore()
    mockAxios.restore()
    vi.clearAllMocks()
  })

  it('401 with valid refresh token → fetches new token and retries original request', async () => {
    const logoutSpy = setupLogoutSpy()

    // First call: 401 (token expired)
    // After refresh: 200
    let callCount = 0
    mockClient.onGet('/protected').reply(() => {
      callCount++
      if (callCount === 1) return [401, { detail: 'Token expired' }]
      return [200, { data: 'secret' }]
    })

    // Mock the plain axios refresh call — only access_token in body, refresh token is a cookie
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: 'new-access-token',
      token_type: 'bearer',
    })

    const result = await apiClient.get('/protected')
    expect(result.data).toEqual({ data: 'secret' })
    expect(tokenStore.getToken()).toBe('new-access-token')
    expect(logoutSpy).not.toHaveBeenCalled()
  })

  it('401 with invalid/expired refresh token → clears session and signals logout', async () => {
    const logoutSpy = setupLogoutSpy()

    mockClient.onGet('/protected').reply(401, { detail: 'Token expired' })
    // Refresh fails
    mockAxios.onPost('/api/v1/auth/refresh').reply(401, { detail: 'Refresh token expired' })

    await expect(apiClient.get('/protected')).rejects.toThrow()

    expect(tokenStore.getToken()).toBeNull()
    expect(tokenStore.getRefreshToken()).toBeNull()
    expect(logoutSpy).toHaveBeenCalledOnce()
  })

  it('already-retried request getting 401 again → no second refresh, forces logout', async () => {
    const logoutSpy = setupLogoutSpy()

    // First 401 → triggers refresh → retry → second 401 (still fails)
    mockClient.onGet('/protected').reply(401, { detail: 'Token expired' })
    mockAxios.onPost('/api/v1/auth/refresh').reply(200, {
      access_token: 'new-token',
      token_type: 'bearer',
    })

    await expect(apiClient.get('/protected')).rejects.toThrow()

    // Logout should have been called because retry also failed with 401
    expect(logoutSpy).toHaveBeenCalled()
  })
})

describe('api response interceptor — concurrent requests', () => {
  let mockClient: MockAdapter
  let mockAxios: MockAdapter

  beforeEach(() => {
    mockClient = new MockAdapter(apiClient)
    mockAxios = new MockAdapter(axios)
    tokenStore.clearAll()
    tokenStore.setToken('expired-token')
    // Refresh token now travels as an httpOnly cookie — no in-memory store needed
    registerLogoutCallback(() => undefined)
  })

  afterEach(() => {
    mockClient.restore()
    mockAxios.restore()
    vi.clearAllMocks()
  })

  it('concurrent 401s share a single refresh call', async () => {
    let refreshCallCount = 0

    mockClient.onGet('/endpoint-a').reply(401)
    mockClient.onGet('/endpoint-b').reply(401)

    mockAxios.onPost('/api/v1/auth/refresh').reply(() => {
      refreshCallCount++
      return [200, { access_token: 'fresh-token', token_type: 'bearer' }]
    })

    // Both fail on retry since mock always returns 401 for the endpoints
    await Promise.allSettled([
      apiClient.get('/endpoint-a'),
      apiClient.get('/endpoint-b'),
    ])

    // Only one refresh should have been fired despite two concurrent 401s
    expect(refreshCallCount).toBeLessThanOrEqual(1)
  })
})
