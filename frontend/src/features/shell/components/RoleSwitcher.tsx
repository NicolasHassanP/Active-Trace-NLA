import { useState, useRef, useEffect } from 'react'
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

const ROLE_LABEL: Record<string, string> = {
  COORDINADOR: 'Coordinador',
  PROFESOR:    'Profesor',
  ALUMNO:      'Alumno',
  ADMIN:       'Administrador',
  FINANZAS:    'Finanzas',
  TUTOR:       'Tutor',
  NEXO:        'Nexo',
}

function gradient(role: Role): string {
  return ROLE_GRADIENT[role] ?? 'linear-gradient(150deg, #94a3b8, #475569)'
}

interface RoleSwitcherProps {
  roles: Role[]
  name?: string
  email?: string
}

function initials(name?: string, email?: string): string {
  if (name) return name.slice(0, 2).toUpperCase()
  if (email) return email.slice(0, 2).toUpperCase()
  return 'U'
}

export function RoleSwitcher({ roles, name, email }: RoleSwitcherProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [open])

  const activeRole = roles[0]
  const otherRoles = roles.slice(1)

  return (
    <div ref={ref} className="relative mt-3">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-[10px] p-[10px] rounded-[11px] border border-line cursor-pointer hover:bg-[#fafbff] transition-colors"
      >
        <div
          className="w-[34px] h-[34px] rounded-full shrink-0 flex items-center justify-center text-white text-[13px] font-bold"
          style={{ background: gradient(activeRole) }}
        >
          {initials(name, email)}
        </div>
        <div className="min-w-0 text-left flex-1">
          <p className="text-[13px] font-extrabold text-ink truncate">{name ?? email ?? 'Usuario'}</p>
          <p className="text-[11.5px] text-faint">{ROLE_LABEL[activeRole] ?? activeRole}</p>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={['w-[13px] h-[13px] text-faint shrink-0 transition-transform', open ? 'rotate-180' : ''].join(' ')}
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && otherRoles.length > 0 && (
        <div
          className="absolute bottom-full left-0 right-0 mb-[6px] bg-white border border-line rounded-[14px] overflow-hidden z-50"
          style={{ boxShadow: '0 30px 80px rgba(16,24,40,.32)' }}
        >
          {roles.map((role) => (
            <div
              key={role}
              className="flex items-center gap-[11px] px-[13px] py-[11px] hover:bg-[#fafbff] cursor-pointer transition-colors"
            >
              <div
                className="w-[32px] h-[32px] rounded-[9px] shrink-0 flex items-center justify-center text-white text-[12px] font-bold"
                style={{ background: gradient(role) }}
              >
                {initials(name, email)}
              </div>
              <div>
                <p className="text-[13.5px] font-extrabold text-ink">{ROLE_LABEL[role] ?? role}</p>
                <p className="text-[11.5px] text-faint">{name ?? email ?? ''}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
