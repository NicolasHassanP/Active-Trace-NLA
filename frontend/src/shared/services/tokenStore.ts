/**
 * tokenStore — in-memory token storage module.
 *
 * Access token and refresh token live ONLY in module state (closure).
 * NEVER uses localStorage or sessionStorage.
 *
 * Design: module with state in closure, not a singleton class.
 */

let _accessToken: string | null = null
let _refreshToken: string | null = null

export function getToken(): string | null {
  return _accessToken
}

export function setToken(token: string): void {
  _accessToken = token
}

export function clearToken(): void {
  _accessToken = null
}

export function getRefreshToken(): string | null {
  return _refreshToken
}

export function setRefreshToken(token: string): void {
  _refreshToken = token
}

export function clearRefreshToken(): void {
  _refreshToken = null
}

export function clearAll(): void {
  _accessToken = null
  _refreshToken = null
}
