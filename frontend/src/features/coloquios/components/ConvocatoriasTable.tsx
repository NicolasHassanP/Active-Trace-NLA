/**
 * ConvocatoriasTable — displays list of convocatorias with metrics and action buttons.
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import type { ConvocatoriaMetricasRead } from '../types'

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
      <p data-testid="convocatorias-empty" className="text-sm text-gray-500 py-4">
        No hay convocatorias activas.
      </p>
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
                {conv.cerrada ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                    Cerrada
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                    Activa
                  </span>
                )}
              </td>
              <td className="px-4 py-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => onImportar(conv.id)}
                  className="text-xs rounded bg-blue-50 px-2 py-1 text-blue-700 hover:bg-blue-100"
                >
                  Importar
                </button>
                {!conv.cerrada && (
                  <button
                    type="button"
                    onClick={() => onCerrar(conv.id)}
                    className="text-xs rounded bg-red-50 px-2 py-1 text-red-700 hover:bg-red-100"
                  >
                    Cerrar
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onVerResultados(conv.id)}
                  className="text-xs rounded bg-gray-50 px-2 py-1 text-gray-700 hover:bg-gray-100"
                >
                  Resultados
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
