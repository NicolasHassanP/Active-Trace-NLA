/**
 * ReporteMateriaHeader — shows aggregate metrics for a materia×cohorte.
 * Handles sin_datos=true gracefully. < 200 LOC.
 */
import type { ReporteMateria } from '../types'
import { Card, CardContent } from '@/shared/components/ui'

interface Props {
  reporte: ReporteMateria | undefined
  isLoading: boolean
}

export default function ReporteMateriaHeader({ reporte, isLoading }: Props) {
  if (isLoading) {
    return <div className="animate-pulse h-16 bg-gray-100 rounded" />
  }

  if (!reporte) return null

  if (reporte.sin_datos) {
    return (
      <div
        className="p-4 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800"
        data-testid="reporte-sin-datos"
      >
        Aún no hay datos suficientes para mostrar métricas de esta materia.
      </div>
    )
  }

  const tasaPercent = (reporte.tasa_aprobacion * 100).toFixed(1)

  return (
    <div className="grid grid-cols-3 gap-4" data-testid="reporte-metrics">
      <Card>
        <CardContent className="text-center">
          <p className="text-2xl font-bold text-gray-900">{reporte.total_alumnos}</p>
          <p className="text-xs text-gray-500 mt-1">Total alumnos</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="text-center">
          <p className="text-2xl font-bold text-red-600">{reporte.total_atrasados}</p>
          <p className="text-xs text-gray-500 mt-1">Atrasados</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="text-center">
          <p className="text-2xl font-bold text-green-600">{tasaPercent}%</p>
          <p className="text-xs text-gray-500 mt-1">Tasa de aprobación</p>
        </CardContent>
      </Card>
    </div>
  )
}
