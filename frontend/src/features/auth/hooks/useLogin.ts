/**
 * useLogin — TanStack Query mutation for login.
 * On success: hydrates auth state via AuthContext.login().
 */
import { useMutation } from '@tanstack/react-query'
import { useAuth } from './useAuth'
import type { LoginParams } from './AuthContext'

export function useLogin() {
  const { login } = useAuth()

  return useMutation({
    mutationFn: (params: LoginParams) => login(params),
  })
}
