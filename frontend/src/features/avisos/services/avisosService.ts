/**
 * avisosService — wraps C-15 Avisos API endpoints.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 *
 * Also exports avisoFormSchema (Zod) for task 2.5 — scope-context coherence.
 */
import { z } from 'zod'
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  AcknowledgmentRead,
  ActualizarAvisoRequest,
  AvisoRead,
  CrearAvisoRequest,
} from '../types'

// ---------------------------------------------------------------------------
// Task 2.5 — Zod schema for aviso form
// Scope-context coherence: if alcance != Global, the relevant context is required.
// ---------------------------------------------------------------------------

export const avisoFormSchema = z
  .object({
    alcance: z.enum(['Global', 'PorMateria', 'PorCohorte', 'PorRol']),
    materia_id: z.string().optional().nullable(),
    cohorte_id: z.string().optional().nullable(),
    rol_destino: z.string().optional().nullable(),
    severidad: z.enum(['Info', 'Advertencia', 'Critico']).default('Info'),
    titulo: z.string().min(1, 'Título obligatorio'),
    cuerpo: z.string().min(1, 'Cuerpo obligatorio'),
    inicio_en: z.string().min(1, 'Inicio obligatorio'),
    fin_en: z.string().min(1, 'Fin obligatorio'),
    orden: z.number().int().default(100),
    activo: z.boolean().default(true),
    requiere_ack: z.boolean().default(false),
  })
  .superRefine((data, ctx) => {
    if (data.alcance === 'PorMateria' && !data.materia_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'materia_id es obligatorio cuando alcance es PorMateria',
        path: ['materia_id'],
      })
    }
    if (data.alcance === 'PorCohorte' && !data.cohorte_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'cohorte_id es obligatorio cuando alcance es PorCohorte',
        path: ['cohorte_id'],
      })
    }
    if (data.alcance === 'PorRol' && !data.rol_destino) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'rol_destino es obligatorio cuando alcance es PorRol',
        path: ['rol_destino'],
      })
    }
  })

export type AvisoFormValues = z.infer<typeof avisoFormSchema>

// ---------------------------------------------------------------------------
// Task 2.2 — gestión
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/avisos — publish a new aviso.
 * Requires avisos:publicar permission.
 */
export async function crearAviso(body: CrearAvisoRequest): Promise<AvisoRead> {
  try {
    const response = await apiClient.post<AvisoRead>('/avisos', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PUT /api/v1/avisos/{aviso_id} — update an existing aviso (partial).
 * Returns 404 if not found in tenant.
 */
export async function actualizarAviso(
  avisoId: string,
  body: ActualizarAvisoRequest,
): Promise<AvisoRead> {
  try {
    const response = await apiClient.put<AvisoRead>(`/avisos/${avisoId}`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /api/v1/avisos/{aviso_id} — soft-delete an aviso.
 * Returns 204 on success, 404 if not found in tenant.
 */
export async function eliminarAviso(avisoId: string): Promise<void> {
  try {
    await apiClient.delete(`/avisos/${avisoId}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/avisos/gestion — management list.
 * Returns ALL non-deleted tenant avisos (no audience filter).
 * Requires avisos:publicar permission. OQ-1 resolved endpoint.
 */
export async function listarGestion(): Promise<AvisoRead[]> {
  try {
    const response = await apiClient.get<AvisoRead[]>('/avisos/gestion')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 2.3 — feed
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/avisos — full recipient feed for authenticated user.
 * Optional cohorte_id filter.
 */
export async function listarFeed(cohorteId?: string): Promise<AvisoRead[]> {
  try {
    const response = await apiClient.get<AvisoRead[]>('/avisos', {
      params: cohorteId ? { cohorte_id: cohorteId } : undefined,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/avisos/pendientes — pending avisos (requiere_ack=True, not yet acked).
 */
export async function listarPendientes(cohorteId?: string): Promise<AvisoRead[]> {
  try {
    const response = await apiClient.get<AvisoRead[]>('/avisos/pendientes', {
      params: cohorteId ? { cohorte_id: cohorteId } : undefined,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 2.4 — ack
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/avisos/{aviso_id}/ack — confirm reading of an aviso (idempotent).
 * usuario_id always from JWT. Returns 403 outside window, 404 if not found.
 */
export async function ackAviso(avisoId: string): Promise<AcknowledgmentRead> {
  try {
    const response = await apiClient.post<AcknowledgmentRead>(`/avisos/${avisoId}/ack`, {})
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
