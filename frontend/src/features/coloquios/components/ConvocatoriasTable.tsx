/**
 * ConvocatoriasTable — displays list of convocatorias with metrics and action buttons.
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import type { ConvocatoriaMetricasRead } from '../types'
import { EmptyState, StatusBadge, Button } from '@/shared/components/ui'

interface Props {
  convocatorias: ConvocatoriaMetricasRead[]
  onImportar: (id: string) => void
  onCerrar: (id: string) => void
  onVerResultados: (id: string) => void
}

export default function ConvocatoriasTable({
  convocatorias,
  onImportar,
  onCerrar,
  onVerResultados,
}: Props) {
  if (convocatorias.length === 0) {
    return (
      <div data-testid="convocatorias-empty">
        <EmptyState title="No hay convocatorias activas." />
      </div>
    )
  }

  return (
    <div data-testid="convocatorias-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Instancia
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Tipo
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
              Convocados
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
              Reservas
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
              Cupos libres
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {convocatorias.map((conv) => (
            <tr key={conv.id}>
              <td className="px-4 py-3 text-gray-900">{conv.instancia}</td>
              <td className="px-4 py-3 text-gray-700 capitalize">{conv.tipo}</td>
              <td className="px-4 py-3 text-right text-gray-700">{conv.convocados}</td>
              <td className="px-4 py-3 text-right text-gray-700">{conv.reservas_activas}</td>
              <td className="px-4 py-3 text-right text-gray-700">{conv.cupos_libres}</td>
              <td className="px-4 py-3">
                <StatusBadge status={conv.cerrada ? 'cancelado' : 'activo'} label={conv.cerrada ? 'Cerrada' : 'Activa'} />
              </td>
              <td className="px-4 py-3 flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => onImportar(conv.id)}>
                  Importar
                </Button>
                {!conv.cerrada && (
                  <Button variant="danger" size="sm" onClick={() => onCerrar(conv.id)}>
                    Cerrar
                  </Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => onVerResultados(conv.id)}>
                  Resultados
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
