/**
 * Tests for convocatoriaSchema Zod validation.
 * Task 6.8 — TDD: RED first, then GREEN.
 * Covers:
 *   - cupo_total > 0 required (cupo <= 0 fails)
 *   - dias_disponibles present (> 0 required to have turnos)
 *   - Happy path: valid convocatoria passes
 *   - Edge cases: empty turnos, exactly cupo=1
 */
import { describe, it, expect } from 'vitest'
import { convocatoriaSchema } from '../convocatoriaSchema'

const validConvocatoria = {
  materia_id: 'mat-uuid-1',
  cohorte_id: 'coh-uuid-1',
  tipo: 'Coloquio' as const,
  instancia: 'Primera',
  dias_disponibles: 2,
  turnos: [
    { fecha: '2024-06-10', cupo_total: 15, franja: null },
  ],
}

describe('convocatoriaSchema', () => {
  it('passes for a valid convocatoria with positive cupo', () => {
    const result = convocatoriaSchema.safeParse(validConvocatoria)
    expect(result.success).toBe(true)
  })

  it('passes with cupo_total exactly 1 (minimum positive)', () => {
    const data = { ...validConvocatoria, turnos: [{ fecha: '2024-06-10', cupo_total: 1 }] }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(true)
  })

  it('fails when cupo_total is 0', () => {
    const data = { ...validConvocatoria, turnos: [{ fecha: '2024-06-10', cupo_total: 0 }] }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
    if (!result.success) {
      const flatErrors = result.error.flatten()
      const fieldErrors = JSON.stringify(flatErrors)
      expect(fieldErrors).toContain('cupo_total')
    }
  })

  it('fails when cupo_total is negative', () => {
    const data = { ...validConvocatoria, turnos: [{ fecha: '2024-06-10', cupo_total: -5 }] }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
  })

  it('fails when dias_disponibles is 0', () => {
    const data = { ...validConvocatoria, dias_disponibles: 0 }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
    if (!result.success) {
      const flat = result.error.flatten()
      const errors = JSON.stringify(flat)
      expect(errors).toContain('dias_disponibles')
    }
  })

  it('fails when dias_disponibles is negative', () => {
    const data = { ...validConvocatoria, dias_disponibles: -1 }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
  })

  it('fails when instancia is empty string', () => {
    const data = { ...validConvocatoria, instancia: '' }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
  })

  it('fails when turnos array is empty', () => {
    const data = { ...validConvocatoria, turnos: [] }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
  })

  it('passes with multiple turnos all having positive cupo', () => {
    const data = {
      ...validConvocatoria,
      turnos: [
        { fecha: '2024-06-10', cupo_total: 10 },
        { fecha: '2024-06-11', cupo_total: 15 },
      ],
    }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(true)
  })

  it('fails when any turno has cupo <= 0 in a multi-turno array', () => {
    const data = {
      ...validConvocatoria,
      turnos: [
        { fecha: '2024-06-10', cupo_total: 10 },
        { fecha: '2024-06-11', cupo_total: 0 },
      ],
    }
    const result = convocatoriaSchema.safeParse(data)
    expect(result.success).toBe(false)
  })
})
