/**
 * MetricasPanel — displays global coloquios metrics (F7.1).
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import type { MetricasRead } from '../types'

interface Props {
  metricas: MetricasRead
}

interface StatCardProps {
  label: string
  value: number
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm border border-gray-100">
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold text-gray-900">{value}</dd>
    </div>
  )
}

export default function MetricasPanel({ metricas: m }: Props) {
  return (
    <dl data-testid="metricas-panel" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <StatCard label="Convocatorias activas" value={m.convocatorias_activas} />
      <StatCard label="Alumnos cargados" value={m.alumnos_cargados} />
      <StatCard label="Reservas activas" value={m.reservas_activas} />
      <StatCard label="Notas registradas" value={m.notas_registradas} />
    </dl>
  )
}
