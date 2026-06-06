/**
 * AvisosTable — management table of all tenant avisos.
 * Used in COORDINADOR/ADMIN management panel.
 * Task 2.7. < 200 LOC.
 */
import type { AvisoRead } from '../types'
import { EmptyState } from '@/shared/components/ui'

interface Props {
  avisos: AvisoRead[]
  onEdit?: (aviso: AvisoRead) => void
  onDelete?: (avisoId: string) => void
}

export default function AvisosTable({ avisos, onEdit, onDelete }: Props) {
  if (avisos.length === 0) {
    return <EmptyState title="No hay avisos publicados." />
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Título</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Alcance</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Severidad</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Activo</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Ack</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {avisos.map((aviso) => (
            <tr key={aviso.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-800">{aviso.titulo}</td>
              <td className="px-4 py-3 text-gray-600">{aviso.alcance}</td>
              <td className="px-4 py-3 text-gray-600">{aviso.severidad}</td>
              <td className="px-4 py-3">{aviso.activo ? 'Sí' : 'No'}</td>
              <td className="px-4 py-3">{aviso.ack_count}</td>
              <td className="px-4 py-3 flex gap-2">
                {onEdit && (
                  <button
                    onClick={() => onEdit(aviso)}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    Editar
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => onDelete(aviso.id)}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Eliminar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
