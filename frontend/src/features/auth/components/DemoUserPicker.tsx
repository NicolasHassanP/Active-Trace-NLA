interface DemoUser {
  email: string
  password: string
  role: string
  roleLabel: string
  nombre: string
  apellidos: string
  gradient: string
}

const DEMO_USERS: DemoUser[] = [
  {
    email:     'coordinador@demo.com',
    password:  'Demo1234!',
    role:      'COORDINADOR',
    roleLabel: 'Coordinador',
    nombre:    'Mariana',
    apellidos: 'Suárez',
    gradient:  'linear-gradient(150deg, #818cf8, #4338ca)',
  },
  {
    email:     'profesor@demo.com',
    password:  'Demo1234!',
    role:      'PROFESOR',
    roleLabel: 'Profesor',
    nombre:    'Sofía',
    apellidos: 'Ledesma',
    gradient:  'linear-gradient(150deg, #34d399, #0a9488)',
  },
  {
    email:     'alumno@demo.com',
    password:  'Demo1234!',
    role:      'ALUMNO',
    roleLabel: 'Alumno',
    nombre:    'Joaquín',
    apellidos: 'Sosa',
    gradient:  'linear-gradient(150deg, #fbbf24, #d97706)',
  },
  {
    email:     'admin@demo.com',
    password:  'Admin1234!',
    role:      'ADMIN',
    roleLabel: 'Administrador',
    nombre:    'Lucia',
    apellidos: 'Ferrer',
    gradient:  'linear-gradient(150deg, #f472b6, #be185d)',
  },
  {
    email:     'tutor@demo.com',
    password:  'Demo1234!',
    role:      'TUTOR',
    roleLabel: 'Tutor',
    nombre:    'Carlos',
    apellidos: 'Mendez',
    gradient:  'linear-gradient(150deg, #38bdf8, #0369a1)',
  },
]

interface DemoUserPickerProps {
  onSelect: (email: string, password: string) => void
  loading?: boolean
}

function initials(nombre: string, apellidos: string): string {
  return (nombre[0] + apellidos[0]).toUpperCase()
}

export function DemoUserPicker({ onSelect, loading = false }: DemoUserPickerProps) {
  return (
    <div className="mt-6">
      <p className="text-[11px] font-bold tracking-[0.5px] uppercase text-faint mb-[10px] px-[2px]">
        Acceso rápido demo
      </p>
      <div className="flex flex-col gap-[6px]">
        {DEMO_USERS.map((u) => (
          <button
            key={u.email}
            type="button"
            disabled={loading}
            onClick={() => onSelect(u.email, u.password)}
            className="flex items-center gap-[12px] p-[12px] rounded-[12px] border border-line bg-white hover:bg-[#fafbff] hover:border-[#d4d8e8] transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed group"
            style={{ boxShadow: '0 1px 2px rgba(16,24,40,.04)' }}
          >
            {/* Avatar */}
            <div
              className="w-[36px] h-[36px] rounded-[10px] shrink-0 flex items-center justify-center text-white text-[13px] font-bold"
              style={{ background: u.gradient }}
            >
              {initials(u.nombre, u.apellidos)}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="text-[13.5px] font-extrabold text-ink">{u.roleLabel}</p>
              <p className="text-[11.5px] text-faint truncate">
                {u.nombre} {u.apellidos}
              </p>
            </div>

            {/* Arrow */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-[14px] h-[14px] text-faint shrink-0 group-hover:text-ind transition-colors"
              aria-hidden="true"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        ))}
      </div>
    </div>
  )
}
