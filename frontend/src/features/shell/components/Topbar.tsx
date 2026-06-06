import { useNavigate } from 'react-router-dom'
import { NavIcon } from '@/shared/components/ui/NavIcon'
import { useAvisosPendientes } from '@/features/avisos/hooks/avisosHooks'

export default function Topbar() {
  const navigate = useNavigate()
  const pendientesQuery = useAvisosPendientes()
  const pendingCount = pendientesQuery.data?.length ?? 0

  return (
    <header
      role="banner"
      className="flex items-center justify-end border-b border-line shrink-0"
      style={{
        height: 60,
        padding: '0 28px',
        background: 'rgba(255,255,255,.85)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <button
        type="button"
        onClick={() => navigate('/avisos')}
        className="relative w-[36px] h-[36px] rounded-[10px] border border-line bg-white flex items-center justify-center text-mut hover:bg-[#f6f7fb] transition-colors"
        aria-label={pendingCount > 0 ? `${pendingCount} avisos pendientes` : 'Notificaciones'}
      >
        <NavIcon name="bell" className="w-[16px] h-[16px]" />
        {pendingCount > 0 && (
          <span
            className="absolute -top-[4px] -right-[4px] min-w-[16px] h-[16px] rounded-full bg-warn text-white text-[10px] font-bold flex items-center justify-center px-[3px] leading-none"
            aria-hidden="true"
          >
            {pendingCount > 99 ? '99+' : pendingCount}
          </span>
        )}
      </button>
    </header>
  )
}
