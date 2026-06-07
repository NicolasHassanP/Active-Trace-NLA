/**
 * Wire types for Comunicaciones feature — mirrors C-12 backend schemas (snake_case).
 * All `estado` values are explicit literal unions — no `any`.
 */

/** Full state machine for a comunicacion message */
export type EstadoComunicacion =
  | 'Pendiente'
  | 'Enviando'
  | 'Enviado'
  | 'Fallido'
  | 'Cancelado'

/** A single communication message record */
export interface ComunicacionRead {
  id: string
  lote_id: string
  destinatario_email: string
  asunto: string
  cuerpo: string
  estado: EstadoComunicacion
  creado_en: string
  actualizado_en: string
}

// ---- Preview ----

export interface PreviewRequest {
  asunto_plantilla: string
  cuerpo_plantilla: string
  /** One sample destinatario's variables for preview rendering */
  variables: Record<string, string>
}

export interface PreviewResponse {
  asunto: string
  cuerpo: string
}

// ---- Encolar ----

/** Request for POST /comunicaciones/encolar */
export interface EncolarRequest {
  destinatarios: string[]
  asunto_plantilla: string
  cuerpo_plantilla: string
  /** Dict keyed by email → { variable: valor } — mirrors backend Dict[str, Dict[str, Any]] */
  variables_por_destinatario: Record<string, Record<string, string>>
}

/** Response from POST /comunicaciones/encolar (201) */
export interface EncolarResponse {
  lote_id: string
  total_encolados: number
}

// ---- Lote ----

export interface LoteStatusResponse {
  lote_id: string
  mensajes: ComunicacionRead[]
  pendientes: number
  enviados: number
  fallidos: number
  cancelados: number
}

// ---- Lote actions ----

export interface LoteRequest {
  lote_id: string
}

export interface IndividualRequest {
  comunicacion_id: string
}

// ---- Mis Envíos (C-27) ----

/** Query params for GET /comunicaciones/mis-envios */
export interface MisEnviosParams {
  estado?: EstadoComunicacion
  offset?: number
  limit?: number
}

/** Paginated response from GET /comunicaciones/mis-envios */
export interface MisEnviosResponse {
  total: number
  offset: number
  limit: number
  items: ComunicacionRead[]
}
