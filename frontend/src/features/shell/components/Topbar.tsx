import { useAuth } from '@/features/auth/hooks/useAuth'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { NavIcon } from '@/shared/components/ui/NavIcon'

export default function Topbar() {
  const { user } = useAuth()
  const logoutMutation = useLogout()

  return (
    <header
      role="banner"
      className="flex items-center gap-[14px] border-b border-line shrink-0"
      style={{
        height: 60,
        padding: '0 28px',
        background: 'rgba(255,255,255,.85)',
        backdropFilter: 'blur(6px)',
      }}
    >
      {/* Buscador */}
      <div
        className="flex items-center gap-[9px] bg-[#f4f5f8] border border-line rounded-[10px] px-[12px] py-[8px] text-faint text-[13px] flex-1"
        style={{ maxWidth: 340 }}
      >
        <NavIcon name="eye" className="w-[14px] h-[14px] shrink-0" />
        <span>Buscar…</span>
      </div>

      <div className="flex items-center gap-[8px] ml-auto">
        {/* Notificaciones */}
        <button
          type="button"
          className="relative w-[36px] h-[36px] rounded-[10px] border border-line bg-white flex items-center justify-center text-mut hover:bg-[#f6f7fb] transition-colors"
          aria-label="Notificaciones"
        >
          <NavIcon name="bell" className="w-[16px] h-[16px]" />
        </button>

        {/* Usuario / logout */}
        {user && (
          <span className="text-[13px] text-mut font-medium hidden sm:block">{user.email}</span>
        )}
        <button
          type="button"
          onClick={() => logoutMutation.mutate()}
          disabled={logoutMutation.isPending}
          className="flex items-center gap-[6px] text-[13px] text-mut hover:text-warn font-semibold transition-colors disabled:opacity-50"
          aria-label="Cerrar sesión"
        >
          <NavIcon name="log-out" className="w-[15px] h-[15px]" />
          <span className="hidden sm:block">Salir</span>
        </button>
      </div>
    </header>
  )
}
