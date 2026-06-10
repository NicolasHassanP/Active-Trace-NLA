/**
 * ReporteMateria — quick consolidated metrics for a materia×cohorte (F2.4).
 * Shows tasa_aprobacion, totales, atrasados. < 200 LOC.
 */
import { useReporteMateria } from '../hooks/calificacionesHooks'
import type { DomainError } from '@/shared/services/domainError'

interface Props {
  materia_id: string
  cohorte_id: string
  actividades?: string[]
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border p-4 bg-white shadow-sm text-center">
      <p className="text-2xl font-bold text-indigo-700">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}

export default function ReporteMateriaPanel({ materia_id, cohorte_id, actividades = [] }: Props) {
  const { data, isLoading, isError, error } = useReporteMateria(materia_id, cohorte_id, actividades)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando reporte…</p>
  }

  if (isError) {
    const de = error as unknown as DomainError
    return (
      <p role="alert" className="text-sm text-red-600">
        {de.detail ?? 'Error al cargar el reporte'}
      </p>
    )
  }

  if (!data || data.sin_datos) {
    return (
      <p className="text-sm text-gray-500 italic">
        Sin datos de calificaciones para esta materia y cohorte.
      </p>
    )
  }

  const tasaPct = (data.tasa_aprobacion * 100).toFixed(1)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard label="Actividades" value={data.total_actividades} />
        <MetricCard label="Alumnos" value={data.total_alumnos} />
        <MetricCard label="Atrasados" value={data.total_atrasados} />
        <MetricCard label="Aprobadas" value={data.total_aprobadas} />
        <MetricCard label="Tasa aprobación" value={`${tasaPct}%`} />
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all"
          style={{ width: `${Math.min(data.tasa_aprobacion * 100, 100)}%` }}
          role="progressbar"
          aria-valuenow={data.tasa_aprobacion * 100}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <p className="text-xs text-gray-500 text-right">{tasaPct}% de aprobación</p>
    </div>
  )
}
