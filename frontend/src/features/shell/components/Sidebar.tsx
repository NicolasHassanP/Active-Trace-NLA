/**
 * Sidebar — navigation sidebar built from user roles.
 *
 * Uses buildNav(roles) to filter the NavItem catalog.
 * Consumes useAuth for session roles.
 */
import { NavLink } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { buildNav } from './buildNav'

export default function Sidebar() {
  const { roles, isInitializing, isAuthenticated } = useAuth()

  if (isInitializing || !isAuthenticated) {
    return null
  }

  const navItems = buildNav(roles)

  if (navItems.length === 0) {
    return (
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col py-4 px-2">
        <p className="text-xs text-gray-400 px-3">Sin ítems de navegación</p>
      </aside>
    )
  }

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col py-4 px-2">
      <nav aria-label="Navegación principal">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
