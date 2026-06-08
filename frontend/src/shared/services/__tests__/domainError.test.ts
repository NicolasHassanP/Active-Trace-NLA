/**
 * Tests for parseDomainError — extracts status + detail from AxiosError
 * RED first: the function does not exist yet.
 */
import { describe, it, expect } from 'vitest'
import axios, { type AxiosError } from 'axios'
import { parseDomainError } from '../domainError'

function makeAxiosError(status: number, detail: unknown): AxiosError {
  // Build a minimal AxiosError-shaped object
  const err = new axios.AxiosError('Request failed', String(status))
  ;(err as ReturnType<typeof Object.create>).response = {
    status,
    data: { detail },
    headers: {},
    config: err.config,
    statusText: String(status),
  }
  return err
}

describe('parseDomainError', () => {
  it('extracts status and string detail from AxiosError with response', () => {
    const err = makeAxiosError(422, 'email duplicado')
    const result = parseDomainError(err)
    expect(result.status).toBe(422)
    expect(result.detail).toBe('email duplicado')
  })

  it('extracts detail from array of objects (FastAPI validation errors)', () => {
    const err = makeAxiosError(422, [{ msg: 'field required', loc: ['body', 'email'] }])
    const result = parseDomainError(err)
    expect(result.status).toBe(422)
    // detail should be a non-empty string representation
    expect(typeof result.detail).toBe('string')
    expect(result.detail.length).toBeGreaterThan(0)
  })

  it('returns status 0 and generic message for non-AxiosError', () => {
    const result = parseDomainError(new Error('network error'))
    expect(result.status).toBe(0)
    expect(result.detail).toMatch(/network error|unexpected/i)
  })

  it('returns status from response when no detail field present', () => {
    const err = makeAxiosError(503, null)
    const result = parseDomainError(err)
    expect(result.status).toBe(503)
  })
})
