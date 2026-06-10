import { Badge } from '@/shared/components/ui/Badge'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import type { InboxHiloRead } from '../types'

interface HilosListProps {
  hilos: InboxHiloRead[]
  selectedHiloId: string | null
  onSelect: (hiloId: string) => void
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

export function HilosList({ hilos, selectedHiloId, onSelect }: HilosListProps) {
  if (hilos.length === 0) {
    return (
      <EmptyState
        title="Sin mensajes"
        description="No tenés hilos de mensajería. Iniciá una conversación."
      />
    )
  }

  return (
    <ul className="divide-y divide-line2">
      {hilos.map((hilo) => {
        const isSelected = hilo.id === selectedHiloId
        return (
          <li key={hilo.id}>
            <button
              type="button"
              onClick={() => onSelect(hilo.id)}
              className={[
                'w-full text-left px-4 py-3 flex flex-col gap-1 transition-colors',
                isSelected ? 'bg-indBg' : 'hover:bg-[#fafbff]',
              ].join(' ')}
            >
              <div className="flex items-center justify-between gap-2">
                <span className={['text-[13.5px] font-semibold truncate', isSelected ? 'text-ind2' : 'text-ink'].join(' ')}>
                  {hilo.asunto ?? '(sin asunto)'}
                </span>
                {hilo.no_leidos > 0 && (
                  <Badge variant="danger">{hilo.no_leidos}</Badge>
                )}
              </div>
              {hilo.ultimo_mensaje_at && (
                <span className="text-[11.5px] text-mut">
                  {formatTimestamp(hilo.ultimo_mensaje_at)}
                </span>
              )}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
