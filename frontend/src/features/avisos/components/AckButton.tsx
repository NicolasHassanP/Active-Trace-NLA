/**
 * AckButton — confirm reading of an aviso.
 * Task 2.7. < 200 LOC.
 */
import { toast } from 'sonner'
import { useAckAviso } from '../hooks/avisosHooks'
import { Button } from '@/shared/components/ui'

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
    <Button
      variant="primary"
      size="sm"
      onClick={handleAck}
      disabled={mutation.isPending}
      isLoading={mutation.isPending}
      data-testid={`ack-btn-${avisoId}`}
    >
      {mutation.isPending ? 'Confirmando…' : 'Confirmar lectura'}
    </Button>
  )
}
