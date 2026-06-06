/**
 * ImportarCandidatosDialog — modal dialog for importing candidates to a convocatoria.
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import { useState } from 'react'
import { useImportarCandidatos } from '../hooks/coloquiosHooks'
import type { ImportarCandidatosRequest } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  evaluacionId: string
  onClose: () => void
  onSuccess?: () => void
}

export default function ImportarCandidatosDialog({ evaluacionId, onClose, onSuccess }: Props) {
  const [alumnoIdsText, setAlumnoIdsText] = useState('')
  const importarMutation = useImportarCandidatos()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const alumno_ids = alumnoIdsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)

    if (alumno_ids.length === 0) return

    const body: ImportarCandidatosRequest = { evaluacion_id: evaluacionId, alumno_ids }
    importarMutation.mutate(
      { evaluacionId, body },
      {
        onSuccess: () => {
          setAlumnoIdsText('')
          onSuccess?.()
          onClose()
        },
      },
    )
  }

  return (
    <div
      data-testid="importar-candidatos-dialog"
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Importar candidatos</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700" htmlFor="alumno-ids">
              IDs de alumnos (uno por línea)
            </label>
            <textarea
              id="alumno-ids"
              rows={6}
              value={alumnoIdsText}
              onChange={(e) => setAlumnoIdsText(e.target.value)}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm font-mono focus:ring-blue-500"
              placeholder="uuid-alumno-1&#10;uuid-alumno-2&#10;..."
            />
          </div>

          {importarMutation.isError && (
            <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
              Error al importar candidatos.
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button variant="secondary" type="button" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={importarMutation.isPending}
              isLoading={importarMutation.isPending}
            >
              {importarMutation.isPending ? 'Importando…' : 'Importar'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
