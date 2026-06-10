/**
 * AvanceKpis — KPIs de avance académico global del alumno.
 * Task 6.1: muestra avance_global_pct, aprobadas y total_actividades.
 */
import { KpiCard } from '@/shared/components/ui/KpiCard'
import type { EstadoAcademicoRead } from '../types'

interface AvanceKpisProps {
  estado: EstadoAcademicoRead
}

function IconProgress() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
    </svg>
  )
}

function IconCheck() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function IconBook() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  )
}

export function AvanceKpis({ estado }: AvanceKpisProps) {
  const variant = estado.avance_global_pct >= 70 ? 'ok' : estado.avance_global_pct >= 40 ? 'amber' : 'warn'

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <KpiCard
        icon={<IconProgress />}
        value={`${estado.avance_global_pct}%`}
        label="Avance global"
        sub={`${estado.aprobadas} de ${estado.total_actividades} actividades aprobadas`}
        variant={variant}
      />
      <KpiCard
        icon={<IconCheck />}
        value={estado.aprobadas}
        label="Actividades aprobadas"
        variant="ok"
      />
      <KpiCard
        icon={<IconBook />}
        value={estado.materias.length}
        label="Materias cursadas"
        variant="ind"
      />
    </div>
  )
}
