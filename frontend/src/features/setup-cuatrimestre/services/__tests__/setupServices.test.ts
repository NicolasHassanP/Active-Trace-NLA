/**
 * TDD — programasService + fechasAcademicasService.
 * Tasks 7.8 + 7.9 — RED first.
 *
 * Scenarios:
 * - crearPrograma: happy path (201), conflict (409), validation (422)
 * - crearFechaAcademica: happy path (201), conflict (409)
 * - Zod schema: programa — titulo required, referencia_archivo required
 * - Zod schema: fecha — numero >= 1, periodo pattern "AAAA-N", titulo required
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { crearPrograma, crearFechaAcademica } from '../setupCuatrimestreService'
import { programaCreateSchema, fechaAcademicaCreateSchema } from '../setupCuatrimestreService'
import type { ProgramaRead, FechaAcademicaRead } from '../../types'

vi.mock('@/shared/services/api', () => ({
  default: {
    post: vi.fn(),
  },
}))

vi.mock('@/shared/services/domainError', () => ({
  parseDomainError: vi.fn((err) => err),
}))

import apiClient from '@/shared/services/api'

const mockPost = vi.mocked(apiClient.post)

beforeEach(() => vi.clearAllMocks())

// ---------------------------------------------------------------------------
// programaCreateSchema
// ---------------------------------------------------------------------------

describe('programaCreateSchema — Zod validation', () => {
  const valid = {
    materia_id: 'mat-1',
    carrera_id: 'car-1',
    cohorte_id: 'coh-1',
    titulo: 'Cálculo I',
    referencia_archivo: 's3://bucket/programa.pdf',
  }

  it('accepts a fully valid programa', () => {
    expect(programaCreateSchema.safeParse(valid).success).toBe(true)
  })

  it('rejects when titulo is empty', () => {
    const result = programaCreateSchema.safeParse({ ...valid, titulo: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('titulo'))).toBe(true)
    }
  })

  it('rejects when referencia_archivo is empty', () => {
    const result = programaCreateSchema.safeParse({ ...valid, referencia_archivo: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('referencia_archivo'))).toBe(true)
    }
  })

  it('rejects when materia_id is missing', () => {
    const { materia_id: _m, ...rest } = valid
    const result = programaCreateSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// fechaAcademicaCreateSchema
// ---------------------------------------------------------------------------

describe('fechaAcademicaCreateSchema — Zod validation', () => {
  const valid = {
    materia_id: 'mat-1',
    cohorte_id: 'coh-1',
    tipo: 'Parcial',
    numero: 1,
    periodo: '2026-1',
    fecha: '2026-04-15',
    titulo: 'Primer Parcial',
  }

  it('accepts a fully valid fecha', () => {
    expect(fechaAcademicaCreateSchema.safeParse(valid).success).toBe(true)
  })

  it('rejects when numero < 1', () => {
    const result = fechaAcademicaCreateSchema.safeParse({ ...valid, numero: 0 })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('numero'))).toBe(true)
    }
  })

  it('rejects periodo not matching AAAA-N pattern', () => {
    const result = fechaAcademicaCreateSchema.safeParse({ ...valid, periodo: '2026' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('periodo'))).toBe(true)
    }
  })

  it('rejects when titulo is empty', () => {
    const result = fechaAcademicaCreateSchema.safeParse({ ...valid, titulo: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('titulo'))).toBe(true)
    }
  })

  it('rejects invalid tipo enum', () => {
    const result = fechaAcademicaCreateSchema.safeParse({ ...valid, tipo: 'Trampa' })
    expect(result.success).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// crearPrograma service
// ---------------------------------------------------------------------------

describe('crearPrograma', () => {
  const body = {
    materia_id: 'mat-1',
    carrera_id: 'car-1',
    cohorte_id: 'coh-1',
    titulo: 'Cálculo I',
    referencia_archivo: 's3://bucket/programa.pdf',
  }
  const responseData: ProgramaRead = {
    id: 'prog-1',
    tenant_id: 'tenant-1',
    materia_id: 'mat-1',
    carrera_id: 'car-1',
    cohorte_id: 'coh-1',
    titulo: 'Cálculo I',
    referencia_archivo: 's3://bucket/programa.pdf',
    cargado_at: null,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-06-01T10:00:00Z',
  }

  it('calls POST /programas and returns ProgramaRead on 201', async () => {
    mockPost.mockResolvedValue({ data: responseData })
    const result = await crearPrograma(body)
    expect(mockPost).toHaveBeenCalledWith('/programas', body)
    expect(result).toEqual(responseData)
  })

  it('throws DomainError on 409 conflict', async () => {
    mockPost.mockRejectedValue({ status: 409, detail: 'Programa ya existe' })
    await expect(crearPrograma(body)).rejects.toMatchObject({ status: 409 })
  })
})

// ---------------------------------------------------------------------------
// crearFechaAcademica service
// ---------------------------------------------------------------------------

describe('crearFechaAcademica', () => {
  const body = {
    materia_id: 'mat-1',
    cohorte_id: 'coh-1',
    tipo: 'Parcial' as const,
    numero: 1,
    periodo: '2026-1',
    fecha: '2026-04-15',
    titulo: 'Primer Parcial',
  }
  const responseData: FechaAcademicaRead = {
    id: 'fecha-1',
    tenant_id: 'tenant-1',
    materia_id: 'mat-1',
    cohorte_id: 'coh-1',
    tipo: 'Parcial',
    numero: 1,
    periodo: '2026-1',
    fecha: '2026-04-15',
    titulo: 'Primer Parcial',
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-06-01T10:00:00Z',
  }

  it('calls POST /fechas-academicas and returns FechaAcademicaRead on 201', async () => {
    mockPost.mockResolvedValue({ data: responseData })
    const result = await crearFechaAcademica(body)
    expect(mockPost).toHaveBeenCalledWith('/fechas-academicas', body)
    expect(result).toEqual(responseData)
  })

  it('throws DomainError on 409 conflict', async () => {
    mockPost.mockRejectedValue({ status: 409, detail: 'Fecha ya existe' })
    await expect(crearFechaAcademica(body)).rejects.toMatchObject({ status: 409 })
  })
})
