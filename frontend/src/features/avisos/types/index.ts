/**
 * Wire types for Avisos feature — mirrors C-15 backend schemas (snake_case).
 * No `any`. Aligned to backend/app/schemas/aviso.py.
 */

/** Alcance del aviso — mirrors app.models.aviso.AvisoAlcance */
export type AvisoAlcance = 'Global' | 'PorMateria' | 'PorCohorte' | 'PorRol'

/** Severidad del aviso — mirrors app.models.aviso.AvisoSeveridad */
export type AvisoSeveridad = 'Info' | 'Advertencia' | 'Critico'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** Respuesta de lectura de un Aviso — mirrors AvisoRead */
export interface AvisoRead {
  id: string
  tenant_id: string
  alcance: AvisoAlcance
  materia_id: string | null
  cohorte_id: string | null
  rol_destino: string | null
  severidad: AvisoSeveridad
  titulo: string
  cuerpo: string
  inicio_en: string    // ISO datetime string
  fin_en: string       // ISO datetime string
  orden: number
  activo: boolean
  requiere_ack: boolean
  ack_count: number    // derived — computed at query time
}

/** Respuesta de lectura de un Acknowledgment — mirrors AcknowledgmentRead */
export interface AcknowledgmentRead {
  id: string
  tenant_id: string
  aviso_id: string
  usuario_id: string
  confirmado_at: string  // ISO datetime string
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/avisos — mirrors CrearAvisoRequest.
 * Scope-context coherence: if alcance != 'Global', the corresponding context
 * field is required. Validated client-side by Zod (task 2.5).
 * tenant_id/actor identity NEVER in body — comes from JWT.
 */
export interface CrearAvisoRequest {
  alcance: AvisoAlcance
  materia_id?: string | null
  cohorte_id?: string | null
  rol_destino?: string | null
  severidad?: AvisoSeveridad
  titulo: string
  cuerpo: string
  inicio_en: string
  fin_en: string
  orden?: number
  activo?: boolean
  requiere_ack?: boolean
}

/**
 * PUT /api/v1/avisos/{id} — mirrors ActualizarAvisoRequest.
 * All fields optional (partial update).
 */
export interface ActualizarAvisoRequest {
  alcance?: AvisoAlcance
  materia_id?: string | null
  cohorte_id?: string | null
  rol_destino?: string | null
  severidad?: AvisoSeveridad
  titulo?: string
  cuerpo?: string
  inicio_en?: string
  fin_en?: string
  orden?: number
  activo?: boolean
  requiere_ack?: boolean
}
