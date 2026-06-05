/**
 * Topbar — top application bar showing user identity and logout.
 */
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useLogout } from '@/features/auth/hooks/useLogout'

export default function Topbar() {
  const { user } = useAuth()
  const logoutMutation = useLogout()

  const handleLogout = () => {
    logoutMutation.mutate()
  }

  return (
    <header
      role="banner"
      className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0"
    >
      <span className="font-semibold text-indigo-700 text-lg">activia-trace</span>

      <div className="flex items-center gap-4">
        {user && (
          <span className="text-sm text-gray-700">{user.email}</span>
        )}
        <button
          type="button"
          onClick={handleLogout}
          disabled={logoutMutation.isPending}
          className="text-sm text-gray-600 hover:text-red-600 font-medium transition-colors disabled:opacity-50"
          aria-label="Cerrar sesión"
        >
          Cerrar sesión
        </button>
      </div>
    </header>
  )
}
