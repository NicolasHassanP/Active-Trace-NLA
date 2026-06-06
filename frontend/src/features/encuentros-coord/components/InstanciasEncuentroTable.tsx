/**
 * InstanciasEncuentroTable — displays a list of InstanciaEncuentroRead rows.
 * Task 5.6. < 200 LOC. Tailwind only.
 */
import type { InstanciaEncuentroRead } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  instancias: InstanciaEncuentroRead[]
}

export default function InstanciasEncuentroTable({ instancias }: Props) {
  if (instancias.length === 0) {
    return (
      <div data-testid="instancias-empty">
        <EmptyState title="No hay instancias de encuentro en el período." />
      </div>
    )
  }

  return (
    <div data-testid="instancias-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Título
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Fecha
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Hora
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Meet
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Grabación
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {instancias.map((inst) => (
            <tr key={inst.id}>
              <td className="px-4 py-3 text-gray-900">{inst.titulo}</td>
              <td className="px-4 py-3 text-gray-700">{inst.fecha}</td>
              <td className="px-4 py-3 text-gray-700">{inst.hora}</td>
              <td className="px-4 py-3">
                <StatusBadge status={inst.estado} />
              </td>
              <td className="px-4 py-3">
                {inst.meet_url ? (
                  <a
                    href={inst.meet_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Unirse
                  </a>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
              <td className="px-4 py-3">
                {inst.video_url ? (
                  <a
                    href={inst.video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Ver grabación
                  </a>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
