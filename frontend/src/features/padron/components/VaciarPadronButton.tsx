/**
 * VaciarPadronButton — empties active padron with confirmation dialog.
 * Handles 204 (success), 404 (not found), 403 (no permission). < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useVaciarPadron } from '../hooks/padronHooks'
import type { DomainError } from '@/shared/services/domainError'

interface Props {
  materia_id: string
  cohorte_id: string
  onSuccess?: () => void
}

export default function VaciarPadronButton({ materia_id, cohorte_id, onSuccess }: Props) {
  const vaciar = useVaciarPadron()
  const [confirming, setConfirming] = useState(false)

  function handleRequest() {
    setConfirming(true)
  }

  function handleCancel() {
    setConfirming(false)
  }

  function handleConfirm() {
    setConfirming(false)
    vaciar.mutate(
      { materia_id, cohorte_id },
      {
        onSuccess: () => {
          toast.success('Padrón vaciado exitosamente')
          onSuccess?.()
        },
        onError: (err) => {
          const de = err as DomainError
          if (de.status === 404) {
            toast.info('No existía un padrón activo para vaciar')
          } else if (de.status === 403) {
            toast.error('Sin permiso: no podés vaciar una versión cargada por otro usuario')
          } else {
            toast.error(`Error al vaciar: ${de.detail}`)
          }
        },
      },
    )
  }

  if (confirming) {
    return (
      <div
        className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded"
        data-testid="vaciar-confirm-dialog"
      >
        <span className="text-sm text-red-800">
          ¿Confirmás el vaciado del padrón? Esta acción no se puede deshacer.
        </span>
        <button
          onClick={handleConfirm}
          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
          data-testid="vaciar-confirm-btn"
        >
          Sí, vaciar
        </button>
        <button
          onClick={handleCancel}
          className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
          data-testid="vaciar-cancel-btn"
        >
          Cancelar
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={handleRequest}
      disabled={vaciar.isPending}
      className="px-3 py-1.5 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50 disabled:opacity-50"
      data-testid="vaciar-padron-btn"
    >
      Vaciar padrón
    </button>
  )
}
