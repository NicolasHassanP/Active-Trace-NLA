import { useAuth } from '@/features/auth/hooks/useAuth'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import type { MensajeRead } from '../types'

interface HiloViewProps {
  mensajes: MensajeRead[]
  isLoading: boolean
}

function formatDateTime(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export function HiloView({ mensajes, isLoading }: HiloViewProps) {
  const { user } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-ind" />
      </div>
    )
  }

  if (mensajes.length === 0) {
    return (
      <EmptyState
        title="Sin mensajes"
        description="Este hilo no tiene mensajes todavía."
      />
    )
  }

  return (
    <div className="flex flex-col gap-3 py-2">
      {mensajes.map((msg) => {
        const isOwn = user?.id === msg.remitente_id
        return (
          <div
            key={msg.id}
            className={['flex flex-col gap-1', isOwn ? 'items-end' : 'items-start'].join(' ')}
          >
            <div
              className={[
                'max-w-[75%] rounded-card px-4 py-3 shadow-card text-[13.5px]',
                isOwn
                  ? 'bg-ind text-white'
                  : 'bg-white border border-line text-ink',
              ].join(' ')}
            >
              {msg.asunto && (
                <p className={['text-[11px] font-bold mb-1 uppercase tracking-wide', isOwn ? 'text-indigo-200' : 'text-mut'].join(' ')}>
                  {msg.asunto}
                </p>
              )}
              <p className="leading-relaxed">{msg.cuerpo}</p>
            </div>
            <span className="text-[11px] text-mut px-1">
              {isOwn ? 'Yo' : 'Otro'} · {formatDateTime(msg.created_at)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
