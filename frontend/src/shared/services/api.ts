/**
 * Centralized Axios client for activia-trace.
 *
 * - baseURL: /api/v1
 * - withCredentials: true (cookie httpOnly of refresh token travels automatically)
 * - Request interceptor: attaches Authorization: Bearer <token> from tokenStore
 * - Response interceptor: handles 401 → refresh → retry (one attempt, flag _retry)
 *   Shared refreshPromise serializes concurrent refresh calls.
 */
import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import * as tokenStore from './tokenStore'

// ---- Logout callback (registered by AuthProvider to clean session state) ----
let _onLogout: (() => void) | null = null

export function registerLogoutCallback(cb: () => void): void {
  _onLogout = cb
}

// ---- Extended config to track retry attempts ----
interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

// ---- Shared refresh promise (serializes concurrent refreshes) ----
let refreshPromise: Promise<string> | null = null

async function doRefresh(): Promise<string> {
  // No body — the refresh token travels as an httpOnly cookie automatically.
  // Use a plain axios call (not the intercepted instance) to avoid infinite loops.
  const response = await axios.post<{ access_token: string }>(
    '/api/v1/auth/refresh',
    undefined,
    { withCredentials: true },
  )
  const newAccessToken = response.data.access_token
  tokenStore.setToken(newAccessToken)
  // Rotated refresh token arrives as a new httpOnly cookie — no JS access needed
  return newAccessToken
}

// ---- Create the Axios instance ----
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
  // FastAPI expects repeated keys for array params (actividades=X&actividades=Y),
  // not the bracket notation Axios uses by default (actividades[]=X&actividades[]=Y).
  paramsSerializer: {
    serialize: (params: Record<string, unknown>) => {
      const parts: string[] = []
      for (const [key, value] of Object.entries(params)) {
        if (Array.isArray(value)) {
          for (const item of value) {
            parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(item))}`)
          }
        } else if (value !== undefined && value !== null) {
          parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
        }
      }
      return parts.join('&')
    },
  },
})

// ---- Request interceptor: attach Bearer token ----
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.getToken()
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// ---- Response interceptor: 401 → refresh → retry ----
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryConfig | undefined

    if (error.response?.status === 401 && originalRequest) {
      // If this request already retried once and still got 401 → force logout (no-loop guard)
      if (originalRequest._retry) {
        tokenStore.clearAll()
        if (_onLogout) {
          _onLogout()
        }
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        // Serialize concurrent refreshes via shared promise
        if (!refreshPromise) {
          refreshPromise = doRefresh().finally(() => {
            refreshPromise = null
          })
        }
        const newToken = await refreshPromise
        // Attach new token to the retried request
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch {
        // Refresh failed — clean session and notify AuthProvider
        tokenStore.clearAll()
        if (_onLogout) {
          _onLogout()
        }
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

export default apiClient
