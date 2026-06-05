/**
 * useLogout — TanStack Query mutation for logout.
 * On success: clears auth state and TanStack Query cache via AuthContext.logout().
 */
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './useAuth'

export function useLogout() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async () => {
      await logout()
    },
    onSuccess: () => {
      navigate('/login', { replace: true })
    },
  })
}
