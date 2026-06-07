/**
 * Wire types for Mensajería feature — mirrors C-20 backend schemas (snake_case).
 * No `any`. Aligned to backend/app/schemas/mensajeria.py.
 */

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** Resumen de hilo en la bandeja — mirrors InboxHiloRead */
export interface InboxHiloRead {
  id: string
  asunto: string | null
  no_leidos: number
  ultimo_mensaje_at: string | null  // ISO datetime string
  otro_participante_nombre: string | null
}

/** Mensaje completo — mirrors MensajeRead */
export interface MensajeRead {
  id: string
  hilo_id: string
  remitente_id: string
  asunto: string
  cuerpo: string
  created_at: string  // ISO datetime string
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/inbox — mirrors HiloCreate.
 * remitente_id y tenant_id NUNCA en el body — vienen del JWT.
 */
export interface HiloCreate {
  destinatario_id: string
  asunto?: string
  cuerpo: string
}

/**
 * POST /api/v1/inbox/{hilo_id}/responder — mirrors RespuestaCreate.
 * remitente_id y tenant_id NUNCA en el body — vienen del JWT.
 */
export interface RespuestaCreate {
  asunto: string
  cuerpo: string
}
