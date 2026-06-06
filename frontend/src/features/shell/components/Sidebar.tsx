import { NavLink } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { buildNav } from './buildNav'
import { NavIcon } from '@/shared/components/ui/NavIcon'
import { RoleSwitcher } from './RoleSwitcher'

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

      {/* Role switcher / user card */}
      {user && (
        <RoleSwitcher roles={roles} name={user.name} email={user.email} />
      )}
    </aside>
  )
}
