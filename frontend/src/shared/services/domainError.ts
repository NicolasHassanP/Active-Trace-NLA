/**
 * domainError — reusable helper for extracting typed error info from AxiosError.
 *
 * All three feature services (padron, atrasados, comunicaciones) use this to
 * translate backend error responses (422/502/503/409/404/403) into a typed object
 * without using `any`.
 */
import axios from 'axios'

export interface DomainError {
  /** HTTP status code, or 0 for non-HTTP errors */
  status: number
  /** Human-readable error message extracted from the response */
  detail: string
}

/**
 * Parses an unknown error thrown by apiClient into a typed DomainError.
 *
 * - AxiosError with response: uses response.status and response.data.detail
 * - AxiosError without response (network): status 0, message from error
 * - Other errors: status 0, message from error
 */
export function parseDomainError(err: unknown): DomainError {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status ?? 0
    const data = err.response?.data as Record<string, unknown> | undefined

    let detail = 'Error inesperado'
    if (data?.detail !== null && data?.detail !== undefined) {
      if (typeof data.detail === 'string') {
        detail = data.detail
      } else if (Array.isArray(data.detail)) {
        // FastAPI validation errors: [{ msg, loc, type }]
        detail = (data.detail as Array<{ msg?: string }>)
          .map((e) => e.msg ?? JSON.stringify(e))
          .join('; ')
      } else {
        detail = JSON.stringify(data.detail)
      }
    } else if (err.message) {
      detail = err.message
    }

    return { status, detail }
  }

  const message = err instanceof Error ? err.message : 'Error inesperado'
  return { status: 0, detail: message }
}
