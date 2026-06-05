/**
 * Tests for decodeJwtPayload — pure function
 *
 * Scenarios:
 * - Valid JWT → returns payload
 * - Malformed token → returns null
 * - Token with wrong number of parts → returns null
 * - Missing required claims → returns null
 */
import { describe, it, expect } from 'vitest'
import { decodeJwtPayload } from '../decodeJwtPayload'

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.fake-sig`
}

describe('decodeJwtPayload', () => {
  it('decodes a valid JWT payload', () => {
    const token = makeJwt({
      sub: 'user-uuid',
      tenant_id: 'tenant-uuid',
      roles: ['ADMIN'],
      exp: 9999999999,
      email: 'admin@test.com',
    })

    const result = decodeJwtPayload(token)
    expect(result).not.toBeNull()
    expect(result?.sub).toBe('user-uuid')
    expect(result?.tenant_id).toBe('tenant-uuid')
    expect(result?.roles).toEqual(['ADMIN'])
    expect(result?.exp).toBe(9999999999)
  })

  it('returns null for malformed base64', () => {
    const result = decodeJwtPayload('header.!!!invalid!!!.sig')
    expect(result).toBeNull()
  })

  it('returns null for wrong number of parts', () => {
    expect(decodeJwtPayload('only.twoparts')).toBeNull()
    expect(decodeJwtPayload('one')).toBeNull()
    expect(decodeJwtPayload('')).toBeNull()
  })

  it('returns null when required claims are missing (no tenant_id)', () => {
    const token = makeJwt({
      sub: 'user-uuid',
      roles: ['ADMIN'],
      exp: 9999999999,
    })
    const result = decodeJwtPayload(token)
    expect(result).toBeNull()
  })

  it('returns null when roles claim is missing', () => {
    const token = makeJwt({
      sub: 'user-uuid',
      tenant_id: 'tenant-uuid',
      exp: 9999999999,
    })
    const result = decodeJwtPayload(token)
    expect(result).toBeNull()
  })
})
