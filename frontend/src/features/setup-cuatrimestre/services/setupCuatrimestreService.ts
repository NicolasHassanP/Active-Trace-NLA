/**
 * setupCuatrimestreService — new endpoints consumed by the Setup wizard.
 *
 * Covers steps 5 and 6 of the wizard:
 *   Step 5: POST /api/v1/programas (task 7.8)
 *   Step 6: POST /api/v1/fechas-academicas (task 7.9)
 *
 * Steps 2–4 and 7 reuse services from equipos and avisos directly.
 * Identity/tenant NEVER in request body — from JWT.
 * Errors wrapped with parseDomainError.
 */
import { z } from 'zod'
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  ProgramaCreateRequest,
  ProgramaRead,
  FechaAcademicaCreateRequest,
  FechaAcademicaRead,
} from '../types'

// ---------------------------------------------------------------------------
// Task 7.8 — Zod schema for ProgramaCreate
// ---------------------------------------------------------------------------

export const programaCreateSchema = z.object({
  materia_id: z.string().min(1, 'materia_id es obligatorio'),
  carrera_id: z.string().min(1, 'carrera_id es obligatorio'),
  cohorte_id: z.string().min(1, 'cohorte_id es obligatorio'),
  titulo: z.string().min(1, 'Título obligatorio'),
  referencia_archivo: z.string().min(1, 'Referencia de archivo obligatoria'),
})

export type ProgramaFormValues = z.infer<typeof programaCreateSchema>

// ---------------------------------------------------------------------------
// Task 7.9 — Zod schema for FechaAcademicaCreate
// Period pattern: "AAAA-N" (e.g. "2026-1")
// ---------------------------------------------------------------------------

const PERIODO_REGEX = /^\d{4}-\d+$/

export const fechaAcademicaCreateSchema = z.object({
  materia_id: z.string().min(1, 'materia_id es obligatorio'),
  cohorte_id: z.string().min(1, 'cohorte_id es obligatorio'),
  tipo: z.enum([
    'Parcial',
    'RecuperatorioParcial',
    'Integrador',
    'RecuperatorioIntegrador',
    'ColoquioEscrito',
    'ColoquioOral',
    'TrabajoPractico',
    'ExamenFinal',
  ]),
  numero: z.number().int().min(1, 'Número debe ser ≥ 1'),
  periodo: z
    .string()
    .regex(PERIODO_REGEX, "Período debe tener formato 'AAAA-N' (ej. '2026-1')"),
  fecha: z.string().min(1, 'Fecha obligatoria'),
  titulo: z.string().min(1, 'Título obligatorio'),
})

export type FechaAcademicaFormValues = z.infer<typeof fechaAcademicaCreateSchema>

// ---------------------------------------------------------------------------
// Task 7.8 — crearPrograma service
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/programas — register a materia program reference.
 * Returns 201 ProgramaRead on success.
 * Throws DomainError on 409 (conflict) or 422 (validation).
 */
export async function crearPrograma(body: ProgramaCreateRequest): Promise<ProgramaRead> {
  try {
    const response = await apiClient.post<ProgramaRead>('/programas', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 7.9 — crearFechaAcademica service
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/fechas-academicas — create an academic date.
 * Returns 201 FechaAcademicaRead on success.
 * Throws DomainError on 409 (conflict — same instancia already active) or 422.
 */
export async function crearFechaAcademica(
  body: FechaAcademicaCreateRequest,
): Promise<FechaAcademicaRead> {
  try {
    const response = await apiClient.post<FechaAcademicaRead>('/fechas-academicas', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
