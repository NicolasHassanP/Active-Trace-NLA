/**
 * Tests for the TareaCreateSchema Zod validation.
 * Task 3.5 — TDD: RED first.
 * Rules:
 *   - asignado_a: required (non-empty string)
 *   - descripcion: required (min length 1)
 *   - contexto_id and contexto_tipo: both null or both present (coherence from D4)
 */
import { describe, it, expect } from 'vitest'
import { tareaCreateSchema } from '../tareaSchema'

describe('tareaCreateSchema — asignado_a required', () => {
  it('passes with valid asignado_a and descripcion', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
      descripcion: 'Revisar actas del coloquio',
    })
    expect(result.success).toBe(true)
  })

  it('fails when asignado_a is empty string', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: '',
      descripcion: 'Descripcion',
    })
    expect(result.success).toBe(false)
    expect(JSON.stringify(result.error?.issues)).toContain('asignado_a')
  })

  it('fails when asignado_a is missing', () => {
    const result = tareaCreateSchema.safeParse({
      descripcion: 'Descripcion',
    })
    expect(result.success).toBe(false)
  })
})

describe('tareaCreateSchema — descripcion required', () => {
  it('fails when descripcion is empty string', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
      descripcion: '',
    })
    expect(result.success).toBe(false)
    expect(JSON.stringify(result.error?.issues)).toContain('descripcion')
  })

  it('fails when descripcion is missing', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
    })
    expect(result.success).toBe(false)
  })
})

describe('tareaCreateSchema — contexto coherence (D4)', () => {
  it('passes when both contexto_id and contexto_tipo are present', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
      descripcion: 'Tarea con contexto',
      contexto_id: 'ctx-uuid',
      contexto_tipo: 'Encuentro',
    })
    expect(result.success).toBe(true)
  })

  it('passes when both contexto_id and contexto_tipo are null', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
      descripcion: 'Tarea sin contexto',
      contexto_id: null,
      contexto_tipo: null,
    })
    expect(result.success).toBe(true)
  })

  it('fails when contexto_id is set but contexto_tipo is null', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
      descripcion: 'Tarea inválida',
      contexto_id: 'ctx-uuid',
      contexto_tipo: null,
    })
    expect(result.success).toBe(false)
  })

  it('fails when contexto_tipo is set but contexto_id is null', () => {
    const result = tareaCreateSchema.safeParse({
      asignado_a: 'user-uuid',
      descripcion: 'Tarea inválida',
      contexto_id: null,
      contexto_tipo: 'Encuentro',
    })
    expect(result.success).toBe(false)
  })
})
