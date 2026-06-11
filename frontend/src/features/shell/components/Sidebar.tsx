import { NavLink } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { buildNav } from './buildNav'
import { NavIcon } from '@/shared/components/ui/NavIcon'
import { RoleSwitcher } from './RoleSwitcher'
import type { NavItem } from '../types'

function groupNavItems(items: NavItem[]): { label: string; items: NavItem[] }[] {
  const groups: { label: string; items: NavItem[] }[] = []
  const map = new Map<string, NavItem[]>()
  for (const item of items) {
    const key = item.group ?? ''
    if (!map.has(key)) {
      const arr: NavItem[] = []
      map.set(key, arr)
      groups.push({ label: key, items: arr })
    }
    map.get(key)!.push(item)
  }
  return groups
}

export default function Sidebar() {
  const { roles, user, isInitializing, isAuthenticated } = useAuth()

  if (isInitializing || !isAuthenticated) return null

  const navItems = buildNav(roles)
  const groups = groupNavItems(navItems)

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
          groups.map(({ label, items }) => (
            <div key={label}>
              {label && (
                <p className="text-[10.5px] font-bold tracking-[0.6px] uppercase text-faint px-[10px] mt-[14px] mb-[4px]">
                  {label}
                </p>
              )}
              <ul>
                {items.map((item) =>
                  item.disabled ? (
                    /* Disabled nav item — visible but not navigable */
                    <li key={item.path}>
                      <span
                        title="Próximamente"
                        className="flex items-center gap-[11px] px-[10px] py-[7.5px] rounded-[9px] mb-[1px] text-[13.5px] font-semibold text-[#9ca3af] cursor-not-allowed select-none"
                        aria-disabled="true"
                      >
                        {item.icon && (
                          <NavIcon name={item.icon} className="w-[15px] h-[15px] shrink-0" />
                        )}
                        {item.label}
                        <span className="ml-auto text-[10px] font-medium bg-gray-100 text-gray-400 rounded px-1.5 py-0.5 leading-tight">
                          Próximamente
                        </span>
                      </span>
                    </li>
                  ) : (
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
                  ),
                )}
              </ul>
            </div>
          ))
        )}
      </nav>

      {/* User card + logout */}
      {user && (
        <RoleSwitcher roles={roles} name={user.name} email={user.email} />
      )}
    </aside>
  )
}
