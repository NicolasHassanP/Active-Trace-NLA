/**
 * VaciarPadronButton — empties active padron with confirmation dialog.
 * Handles 204 (success), 404 (not found), 403 (no permission). < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useVaciarPadron } from '../hooks/padronHooks'
import type { DomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'

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
        <Button
          variant="danger"
          size="sm"
          onClick={handleConfirm}
          data-testid="vaciar-confirm-btn"
        >
          Sí, vaciar
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleCancel}
          data-testid="vaciar-cancel-btn"
        >
          Cancelar
        </Button>
      </div>
    )
  }

  return (
    <Button
      variant="danger"
      size="sm"
      onClick={handleRequest}
      isLoading={vaciar.isPending}
      disabled={vaciar.isPending}
      data-testid="vaciar-padron-btn"
    >
      Vaciar padrón
    </Button>
  )
}
