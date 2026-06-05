import type { JwtPayload } from '../types'

/**
 * Decodes the payload of a JWT token without verifying the signature.
 * The server verifies the signature on every request — the client only
 * reads the claims for UX purposes (hydrating AuthUser, filtering nav).
 *
 * @returns JwtPayload or null if the token is malformed
 */
export function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    // Base64url → Base64 → decode
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '=='.slice(0, (4 - (base64.length % 4)) % 4)
    const json = atob(padded)
    const payload = JSON.parse(json) as JwtPayload

    if (!payload.sub || !payload.tenant_id || !Array.isArray(payload.roles)) {
      return null
    }

    return payload
  } catch {
    return null
  }
}
