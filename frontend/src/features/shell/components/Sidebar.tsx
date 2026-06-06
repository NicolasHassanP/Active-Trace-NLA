import { NavLink } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { buildNav } from './buildNav'
import { NavIcon } from '@/shared/components/ui/NavIcon'
import type { Role } from '@/features/auth/types'

const ROLE_GRADIENT: Record<string, string> = {
  COORDINADOR: 'linear-gradient(150deg, #818cf8, #4338ca)',
  PROFESOR:    'linear-gradient(150deg, #34d399, #0a9488)',
  ALUMNO:      'linear-gradient(150deg, #fbbf24, #d97706)',
  ADMIN:       'linear-gradient(150deg, #f472b6, #be185d)',
  FINANZAS:    'linear-gradient(150deg, #34d399, #047857)',
  TUTOR:       'linear-gradient(150deg, #60a5fa, #2563eb)',
  NEXO:        'linear-gradient(150deg, #a78bfa, #7c3aed)',
}

function avatarGradient(roles: Role[]): string {
  for (const role of roles) {
    if (ROLE_GRADIENT[role]) return ROLE_GRADIENT[role]
  }
  return 'linear-gradient(150deg, #94a3b8, #475569)'
}

function initials(name?: string, email?: string): string {
  if (name) return name.slice(0, 2).toUpperCase()
  if (email) return email.slice(0, 2).toUpperCase()
  return 'U'
}

export default function Sidebar() {
  const { roles, user, isInitializing, isAuthenticated } = useAuth()

  if (isInitializing || !isAuthenticated) return null

  const navItems = buildNav(roles)

  return (
    <aside
      className="flex flex-col bg-white border-r border-line shrink-0"
      style={{ width: 252, padding: '22px 14px 16px' }}
    >
      {/* Brand */}
      <div className="flex items-center gap-[10px] mb-[22px] px-[10px]">
        <div
          className="w-[30px] h-[30px] rounded-[9px] shrink-0"
          style={{
            background: 'linear-gradient(150deg,#6366f1,#4338ca)',
            boxShadow: '0 3px 8px rgba(67,56,202,.35)',
          }}
        />
        <span className="text-[14.5px] font-extrabold text-ink tracking-[-0.3px]">activia-trace</span>
      </div>

      {/* Nav */}
      <nav aria-label="Navegación principal" className="flex-1 overflow-y-auto">
        {navItems.length === 0 ? (
          <p className="text-[11px] text-faint px-[10px]">Sin ítems de navegación</p>
        ) : (
          <ul>
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    [
                      'flex items-center gap-[11px] px-[10px] py-[7.5px] rounded-[9px] mb-[1px] text-[13.5px] font-semibold cursor-pointer transition-colors',
                      isActive
                        ? 'bg-indBg text-ind2'
                        : 'text-[#4b5563] hover:bg-[#f4f4f8] hover:text-ink',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      {item.icon && (
                        <NavIcon
                          name={item.icon}
                          className={['w-[15px] h-[15px] shrink-0', isActive ? 'text-ind' : ''].join(' ')}
                        />
                      )}
                      {item.label}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        )}
      </nav>

      {/* User card */}
      {user && (
        <div className="flex items-center gap-[10px] p-[10px] rounded-[11px] border border-line mt-4">
          <div
            className="w-[34px] h-[34px] rounded-full shrink-0 flex items-center justify-center text-white text-[13px] font-bold"
            style={{ background: avatarGradient(roles) }}
          >
            {initials(user.name, user.email)}
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-bold text-ink truncate">{user.name ?? user.email}</p>
            <p className="text-[11px] text-faint truncate">{roles[0] ?? ''}</p>
          </div>
        </div>
      )}
    </aside>
  )
}
