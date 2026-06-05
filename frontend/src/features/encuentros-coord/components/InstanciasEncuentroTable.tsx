/**
 * InstanciasEncuentroTable — displays a list of InstanciaEncuentroRead rows.
 * Task 5.6. < 200 LOC. Tailwind only.
 */
import type { InstanciaEncuentroRead } from '../types'

interface Props {
  instancias: InstanciaEncuentroRead[]
}

const ESTADO_LABELS: Record<string, string> = {
  programado: 'Programado',
  realizado: 'Realizado',
  cancelado: 'Cancelado',
  postergado: 'Postergado',
}

const ESTADO_COLORS: Record<string, string> = {
  programado: 'bg-blue-100 text-blue-800',
  realizado: 'bg-green-100 text-green-800',
  cancelado: 'bg-red-100 text-red-800',
  postergado: 'bg-yellow-100 text-yellow-800',
}

export default function InstanciasEncuentroTable({ instancias }: Props) {
  if (instancias.length === 0) {
    return (
      <p data-testid="instancias-empty" className="text-sm text-gray-500 py-4">
        No hay instancias de encuentro en el período.
      </p>
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
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ESTADO_COLORS[inst.estado] ?? 'bg-gray-100 text-gray-700'}`}
                >
                  {ESTADO_LABELS[inst.estado] ?? inst.estado}
                </span>
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
