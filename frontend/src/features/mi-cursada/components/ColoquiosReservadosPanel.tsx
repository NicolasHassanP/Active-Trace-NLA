/**
 * ColoquiosReservadosPanel — reservas activas de coloquios del alumno.
 * Task 6.3: EmptyState cuando no hay reservas; lista de cards cuando las hay.
 */
import { EmptyState } from '@/shared/components/ui/EmptyState'
import type { ColoquioReservadoRead } from '../types'

interface ColoquiosReservadosPanelProps {
  coloquios: ColoquioReservadoRead[]
}

function formatFecha(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}

export function ColoquiosReservadosPanel({ coloquios }: ColoquiosReservadosPanelProps) {
  if (coloquios.length === 0) {
    return (
      <EmptyState
        title="Sin coloquios reservados"
        description="No tenés turnos activos de coloquio en este momento."
      />
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {coloquios.map((col) => (
        <div
          key={col.evaluacion_id}
          className="bg-white border border-line rounded-card shadow-card p-4 space-y-1"
        >
          <p className="text-[13px] font-bold text-ink">{col.materia_nombre}</p>
          <p className="text-[12px] text-mut">
            {col.tipo} · Instancia {col.instancia}
          </p>
          <p className="text-[12px] text-ind font-semibold">
            {formatFecha(col.fecha)}
            {col.franja ? ` · ${col.franja}` : ''}
          </p>
        </div>
      ))}
    </div>
  )
}
