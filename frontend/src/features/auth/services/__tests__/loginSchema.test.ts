/**
 * Tests for login Zod schema — task 5.1 RED
 *
 * Scenarios:
 * - Valid email and password → success
 * - Invalid email format → validation error
 * - Empty password → validation error
 * - Missing fields → validation errors
 */
import { describe, it, expect } from 'vitest'
import { loginSchema } from '../loginSchema'

describe('loginSchema', () => {
  it('accepts valid email and password', () => {
    const result = loginSchema.safeParse({ email: 'user@example.com', password: 'secret123' })
    expect(result.success).toBe(true)
  })

  it('rejects invalid email format', () => {
    const result = loginSchema.safeParse({ email: 'not-an-email', password: 'secret123' })
    expect(result.success).toBe(false)
    if (!result.success) {
      const emailError = result.error.issues.find(i => i.path[0] === 'email')
      expect(emailError).toBeDefined()
    }
  })

  it('rejects empty password', () => {
    const result = loginSchema.safeParse({ email: 'user@example.com', password: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      const pwdError = result.error.issues.find(i => i.path[0] === 'password')
      expect(pwdError).toBeDefined()
    }
  })

  it('rejects missing email', () => {
    const result = loginSchema.safeParse({ password: 'secret123' })
    expect(result.success).toBe(false)
  })

  it('rejects missing password', () => {
    const result = loginSchema.safeParse({ email: 'user@example.com' })
    expect(result.success).toBe(false)
  })
})
