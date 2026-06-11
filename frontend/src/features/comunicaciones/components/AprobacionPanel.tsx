/**
 * AprobacionPanel — approve/cancel lote or individual messages.
 * Visible only to users with comunicacion:aprobar permission (COORDINADOR/ADMIN).
 * 409 → toast without breaking view; 404 per row → row-level error. < 200 LOC.
 */
import { toast } from 'sonner'
import { useAprobarLote, useCancelarLote, useAprobarIndividual, useCancelarIndividual } from '../hooks/comunicacionHooks'
import type { DomainError } from '@/shared/services/domainError'
import type { ComunicacionRead } from '../types'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { Button, StatusBadge } from '@/shared/components/ui'

interface Props {
  loteId: string
  mensajes: ComunicacionRead[]
}

/** Roles that can approve/cancel communications */
const APROBAR_ROLES = ['COORDINADOR', 'ADMIN'] as const

export default function AprobacionPanel({ loteId, mensajes }: Props) {
  const { roles } = useAuth()
  const canAprobar = roles.some((r) => (APROBAR_ROLES as readonly string[]).includes(r))

  const aprobarLote = useAprobarLote()
  const cancelarLote = useCancelarLote()
  const aprobarInd = useAprobarIndividual()
  const cancelarInd = useCancelarIndividual()

  if (!canAprobar) return null

  function handleAprobarLote() {
    aprobarLote.mutate(loteId, {
      onSuccess: () => toast.success('Lote aprobado'),
      onError: (err) => {
        const de = err as unknown as DomainError
        toast.error(de.detail ?? 'Error al aprobar el lote')
      },
    })
  }

  function handleCancelarLote() {
    cancelarLote.mutate(loteId, {
      onSuccess: () => toast.success('Lote cancelado'),
      onError: (err) => {
        const de = err as unknown as DomainError
        if (de.status === 409) {
          toast.error('Transición inválida: algunos mensajes no son cancelables')
        } else {
          toast.error(de.detail ?? 'Error al cancelar')
        }
      },
    })
  }

  function handleAprobarIndividual(id: string) {
    aprobarInd.mutate(id, {
      onError: (err) => {
        const de = err as unknown as DomainError
        toast.error(de.status === 404 ? 'Mensaje no encontrado' : de.detail)
      },
    })
  }

  function handleCancelarIndividual(id: string) {
    cancelarInd.mutate(id, {
      onError: (err) => {
        const de = err as unknown as DomainError
        toast.error(de.status === 404 ? 'Mensaje no encontrado' : de.detail)
      },
    })
  }

  return (
    <div className="space-y-4" data-testid="aprobacion-panel">
      <div className="flex gap-3">
        <Button
          onClick={handleAprobarLote}
          isLoading={aprobarLote.isPending}
          size="sm"
          data-testid="aprobar-lote-btn"
        >
          Aprobar lote
        </Button>
        <Button
          variant="danger"
          onClick={handleCancelarLote}
          isLoading={cancelarLote.isPending}
          size="sm"
          data-testid="cancelar-lote-btn"
        >
          Cancelar lote
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-xs border">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-2 py-1 text-left text-gray-600">Destinatario</th>
              <th className="px-2 py-1 text-left text-gray-600">Estado</th>
              <th className="px-2 py-1 text-left text-gray-600">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {mensajes.map((msg) => (
              <tr key={msg.id} className="border-t">
                <td className="px-2 py-1">{msg.destinatario_email}</td>
                <td className="px-2 py-1">
                  <StatusBadge status={msg.estado} />
                </td>
                <td className="px-2 py-1 flex gap-2">
                  {msg.estado === 'Pendiente' && (
                    <>
                      <button
                        onClick={() => handleAprobarIndividual(msg.id)}
                        className="underline text-green-700"
                        data-testid={`aprobar-${msg.id}`}
                      >
                        Aprobar
                      </button>
                      <button
                        onClick={() => handleCancelarIndividual(msg.id)}
                        className="underline text-red-700"
                        data-testid={`cancelar-${msg.id}`}
                      >
                        Cancelar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
