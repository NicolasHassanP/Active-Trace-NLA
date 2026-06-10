/**
 * SyncMoodlePanel — triggers on-demand Moodle sync.
 * 503 → informative notice; 502 → retryable error; 201 → success toast. < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useSyncMoodlePadron } from '../hooks/padronHooks'
import type { DomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'

interface Props {
  materia_id: string
  cohorte_id: string
  course_id: string
}

export default function SyncMoodlePanel({ materia_id, cohorte_id, course_id }: Props) {
  const sync = useSyncMoodlePadron()
  const [localError, setLocalError] = useState<{ kind: '503' | '502' | 'other'; detail: string } | null>(null)

  function handleSync() {
    setLocalError(null)
    sync.mutate(
      { course_id, materia_id, cohorte_id },
      {
        onSuccess: (version) => {
          toast.success(`Sincronización exitosa: ${version.filas_total} filas desde Moodle`)
        },
        onError: (err) => {
          const de = err as unknown as DomainError
          if (de.status === 503) {
            setLocalError({ kind: '503', detail: 'La integración con Moodle no está configurada en este entorno.' })
          } else if (de.status === 502) {
            setLocalError({ kind: '502', detail: de.detail || 'Moodle no está disponible.' })
          } else {
            setLocalError({ kind: 'other', detail: de.detail || 'Error al sincronizar.' })
          }
        },
      },
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Button
          onClick={handleSync}
          isLoading={sync.isPending}
          disabled={sync.isPending}
          data-testid="sync-moodle-btn"
        >
          Sincronizar desde Moodle
        </Button>
      </div>

      {localError?.kind === '503' && (
        <div
          role="status"
          className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800"
          data-testid="sync-503-notice"
        >
          <span className="font-medium">Moodle no configurado:</span>
          <span>{localError.detail}</span>
        </div>
      )}

      {(localError?.kind === '502' || localError?.kind === 'other') && (
        <div
          role="alert"
          className="flex items-start justify-between p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800"
          data-testid="sync-error-notice"
        >
          <span>{localError.detail}</span>
          <button
            onClick={handleSync}
            className="ml-3 underline hover:no-underline"
          >
            Reintentar
          </button>
        </div>
      )}
    </div>
  )
}
