import { useContext } from 'react'
import { AuthContext } from './AuthContext'

/**
 * useAuth — consumes the AuthContext.
 * Must be used inside AuthProvider.
 */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return ctx
}
