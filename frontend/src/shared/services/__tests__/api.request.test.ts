/**
 * Tests for the Axios request interceptor — task 3.1 RED
 *
 * Verifies:
 * - Attaches Authorization: Bearer <token> when token is in memory
 * - Does NOT attach Authorization when no token is in memory
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '../api'
import * as tokenStore from '../tokenStore'

describe('api request interceptor', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    tokenStore.clearAll()
  })

  afterEach(() => {
    mock.restore()
  })

  it('attaches Authorization header when token is present', async () => {
    tokenStore.setToken('test-access-token-123')
    mock.onGet('/test').reply(200, { ok: true })

    await apiClient.get('/test')

    const lastRequest = mock.history.get[0]
    expect(lastRequest.headers?.['Authorization']).toBe('Bearer test-access-token-123')
  })

  it('does NOT attach Authorization header when no token is present', async () => {
    // No token set — tokenStore is clear
    mock.onGet('/test').reply(200, { ok: true })

    await apiClient.get('/test')

    const lastRequest = mock.history.get[0]
    expect(lastRequest.headers?.['Authorization']).toBeUndefined()
  })
})
