/**
 * AckButton — confirm reading of an aviso.
 * Task 2.7. < 200 LOC.
 */
import { toast } from 'sonner'
import { useAckAviso } from '../hooks/avisosHooks'

interface Props {
  avisoId: string
  onAcked?: () => void
}

export default function AckButton({ avisoId, onAcked }: Props) {
  const mutation = useAckAviso()

  function handleAck() {
    mutation.mutate(avisoId, {
      onSuccess: () => {
        toast.success('Lectura confirmada')
        onAcked?.()
      },
      onError: (err) => {
        const detail = (err as { detail?: string }).detail ?? 'Error al confirmar lectura'
        toast.error(detail)
      },
    })
  }

  return (
    <button
      onClick={handleAck}
      disabled={mutation.isPending}
      data-testid={`ack-btn-${avisoId}`}
      className="rounded bg-green-600 px-3 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-50"
    >
      {mutation.isPending ? 'Confirmando…' : 'Confirmar lectura'}
    </button>
  )
}
