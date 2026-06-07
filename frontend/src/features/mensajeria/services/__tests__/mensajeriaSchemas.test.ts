/**
 * Tests for nuevoHiloSchema and responderSchema — Zod validation.
 * Task 7.2: rechazan cuerpo/asunto vacíos; aceptan payloads válidos.
 */
import { describe, it, expect } from 'vitest'
import { nuevoHiloSchema, responderSchema } from '../mensajeriaService'

// ---------------------------------------------------------------------------
// nuevoHiloSchema
// ---------------------------------------------------------------------------
describe('nuevoHiloSchema', () => {
  it('accepts a valid payload with destinatario_id and cuerpo', () => {
    const result = nuevoHiloSchema.safeParse({
      destinatario_id: '550e8400-e29b-41d4-a716-446655440000',
      cuerpo: 'Hola, quería consultarte sobre la entrega.',
    })
    expect(result.success).toBe(true)
  })

  it('accepts a payload with optional asunto', () => {
    const result = nuevoHiloSchema.safeParse({
      destinatario_id: '550e8400-e29b-41d4-a716-446655440000',
      asunto: 'Consulta de notas',
      cuerpo: 'Buenos días.',
    })
    expect(result.success).toBe(true)
  })

  it('rejects when cuerpo is empty string', () => {
    const result = nuevoHiloSchema.safeParse({
      destinatario_id: '550e8400-e29b-41d4-a716-446655440000',
      cuerpo: '',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].path).toContain('cuerpo')
    }
  })

  it('rejects when destinatario_id is not a UUID', () => {
    const result = nuevoHiloSchema.safeParse({
      destinatario_id: 'not-a-uuid',
      cuerpo: 'Hola',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].path).toContain('destinatario_id')
    }
  })

  it('rejects when destinatario_id is missing', () => {
    const result = nuevoHiloSchema.safeParse({ cuerpo: 'Hola' })
    expect(result.success).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// responderSchema
// ---------------------------------------------------------------------------
describe('responderSchema', () => {
  it('accepts a valid payload with asunto and cuerpo', () => {
    const result = responderSchema.safeParse({
      asunto: 'Re: Consulta',
      cuerpo: 'Gracias por tu mensaje.',
    })
    expect(result.success).toBe(true)
  })

  it('rejects when asunto is empty string', () => {
    const result = responderSchema.safeParse({
      asunto: '',
      cuerpo: 'Hola',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].path).toContain('asunto')
    }
  })

  it('rejects when cuerpo is empty string', () => {
    const result = responderSchema.safeParse({
      asunto: 'Re: algo',
      cuerpo: '',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].path).toContain('cuerpo')
    }
  })

  it('rejects when both asunto and cuerpo are missing', () => {
    const result = responderSchema.safeParse({})
    expect(result.success).toBe(false)
  })
})
