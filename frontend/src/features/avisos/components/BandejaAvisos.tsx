/**
 * BandejaAvisos — bandeja de avisos del usuario autenticado.
 * Shows full feed + allows ack on pending avisos.
 * Task 2.7. < 200 LOC.
 */
import AckButton from './AckButton'
import type { AvisoRead } from '../types'
import { EmptyState } from '@/shared/components/ui'

interface Props {
  avisos: AvisoRead[]
  pendientes: AvisoRead[]
  isLoading: boolean
}

const SEVERIDAD_COLOR: Record<string, string> = {
  Info: 'border-blue-300 bg-blue-50',
  Advertencia: 'border-yellow-300 bg-yellow-50',
  Critico: 'border-red-300 bg-red-50',
}

export default function BandejaAvisos({ avisos, pendientes, isLoading }: Props) {
  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando avisos…</p>
  }

  if (avisos.length === 0) {
    return (
      <div data-testid="avisos-empty">
        <EmptyState title="No hay avisos en este momento." />
      </div>
    )
  }

  const pendienteIds = new Set(pendientes.map((a) => a.id))

  return (
    <div className="space-y-3">
      {avisos.map((aviso) => (
        <div
          key={aviso.id}
          className={`rounded-lg border-l-4 p-4 ${SEVERIDAD_COLOR[aviso.severidad] ?? 'border-gray-300 bg-gray-50'}`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="font-medium text-gray-800">{aviso.titulo}</p>
              <p className="mt-1 text-sm text-gray-600">{aviso.cuerpo}</p>
              <p className="mt-2 text-xs text-gray-400">
                {aviso.inicio_en.split('T')[0]} — {aviso.fin_en.split('T')[0]}
              </p>
            </div>
            {pendienteIds.has(aviso.id) && aviso.requiere_ack && (
              <AckButton avisoId={aviso.id} />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
