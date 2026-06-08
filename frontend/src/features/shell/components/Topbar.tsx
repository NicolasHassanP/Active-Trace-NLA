import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { NavIcon } from '@/shared/components/ui/NavIcon'
import { useAvisosPendientes } from '@/features/avisos/hooks/avisosHooks'
import { useNoLeidosInbox } from '@/features/mensajeria/hooks/mensajeriaHooks'
import { useAuth } from '@/features/auth/hooks/useAuth'
import type { Role } from '@/features/auth/types'

const MESSAGING_ROLES: Role[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']

export default function Topbar() {
  const navigate = useNavigate()
  const { roles } = useAuth()
  const hasMessaging = roles.some((r) => MESSAGING_ROLES.includes(r))

  const pendientesQuery = useAvisosPendientes()
  const avisosPending = pendientesQuery.data?.length ?? 0
  const mensajesNoLeidos = useNoLeidosInbox(hasMessaging)
  const totalCount = avisosPending + mensajesNoLeidos

  const [ringing, setRinging] = useState(false)
  const prevCountRef = useRef<number | null>(null)

  useEffect(() => {
    // Skip initial render — only animate on real increases after first data load
    if (prevCountRef.current === null) {
      prevCountRef.current = totalCount
      return
    }
    if (totalCount > prevCountRef.current) {
      setRinging(true)
      const t = setTimeout(() => setRinging(false), 700)
      prevCountRef.current = totalCount
      return () => clearTimeout(t)
    }
    prevCountRef.current = totalCount
  }, [totalCount])

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
        aria-label={totalCount > 0 ? `${totalCount} notificaciones pendientes` : 'Notificaciones'}
      >
        <NavIcon
          name="bell"
          className={`w-[16px] h-[16px] origin-top ${ringing ? 'animate-bell-ring' : ''}`}
        />
        {totalCount > 0 && (
          <span
            className="absolute -top-[4px] -right-[4px] min-w-[16px] h-[16px] rounded-full bg-warn text-white text-[10px] font-bold flex items-center justify-center px-[3px] leading-none"
            aria-hidden="true"
          >
            {totalCount > 99 ? '99+' : totalCount}
          </span>
        )}
      </button>
    </header>
  )
}
