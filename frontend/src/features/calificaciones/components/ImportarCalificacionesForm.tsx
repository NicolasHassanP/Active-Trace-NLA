/**
 * ImportarCalificacionesForm — upload → preview activities → select → confirm import.
 * Two-step: preview returns actividades + filas; import sends them back with selection.
 * < 200 LOC.
 */
import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { useImportarCalificaciones, usePreviewCalificaciones } from '../hooks/calificacionesHooks'
import type { ActividadDetectada, CalificacionFila } from '../types'
import type { DomainError } from '@/shared/services/domainError'
import { Button, Badge } from '@/shared/components/ui'

interface Props {
  materia_id: string
  cohorte_id: string
}

export default function ImportarCalificacionesForm({ materia_id, cohorte_id }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [actividades, setActividades] = useState<ActividadDetectada[]>([])
  const [filas, setFilas] = useState<CalificacionFila[]>([])
  const [seleccionadas, setSeleccionadas] = useState<Set<string>>(new Set())
  const [noEnPadron, setNoEnPadron] = useState<string[]>([])
  const [previewError, setPreviewError] = useState<string | null>(null)

  const preview = usePreviewCalificaciones()
  const importar = useImportarCalificaciones()

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setPreviewError(null)
    setActividades([])
    setFilas([])
    setSeleccionadas(new Set())
    setNoEnPadron([])
    preview.mutate(file, {
      onSuccess: (data) => {
        setActividades(data.actividades)
        setFilas(data.filas)
        setNoEnPadron(data.no_en_padron)
        // Pre-select all activities by default
        setSeleccionadas(new Set(data.actividades.map((a) => a.actividad)))
      },
      onError: (err) => {
        const de = err as DomainError
        setPreviewError(de.detail ?? 'Error al previsualizar el archivo')
      },
    })
  }

  function toggleActividad(nombre: string) {
    setSeleccionadas((prev) => {
      const next = new Set(prev)
      if (next.has(nombre)) {
        next.delete(nombre)
      } else {
        next.add(nombre)
      }
      return next
    })
  }

  function handleConfirm() {
    if (filas.length === 0 || seleccionadas.size === 0) return
    importar.mutate(
      {
        materia_id,
        cohorte_id,
        actividades_seleccionadas: Array.from(seleccionadas),
        filas,
      },
      {
        onSuccess: (cals) => {
          toast.success(`Importación exitosa: ${cals.length} calificaciones guardadas`)
          setActividades([])
          setFilas([])
          setSeleccionadas(new Set())
          setNoEnPadron([])
          if (fileRef.current) fileRef.current.value = ''
        },
        onError: (err) => {
          const de = err as DomainError
          toast.error(`Error al importar: ${de.detail}`)
        },
      },
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Archivo de calificaciones (.xlsx o .csv)
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.csv"
          onChange={handleFileChange}
          disabled={preview.isPending}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          data-testid="cal-file-input"
        />
      </div>

      {preview.isPending && (
        <p className="text-sm text-gray-500">Procesando archivo…</p>
      )}

      {previewError && (
        <div role="alert" className="flex items-start gap-2 rounded border border-red-300 bg-red-50 px-3 py-2">
          <p className="flex-1 text-sm text-red-700">{previewError}</p>
          <button
            onClick={() => setPreviewError(null)}
            className="shrink-0 text-red-400 hover:text-red-600"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
      )}

      {noEnPadron.length > 0 && (
        <div className="rounded border border-yellow-300 bg-yellow-50 p-3">
          <p className="text-sm font-medium text-yellow-800">
            {noEnPadron.length} email(s) no están en el padrón activo y serán omitidos:
          </p>
          <ul className="mt-1 text-xs text-yellow-700 list-disc pl-4">
            {noEnPadron.slice(0, 5).map((e) => <li key={e}>{e}</li>)}
            {noEnPadron.length > 5 && <li>…y {noEnPadron.length - 5} más</li>}
          </ul>
        </div>
      )}

      {actividades.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-700">
            Se detectaron <strong>{actividades.length}</strong> actividades. Seleccioná las que querés importar:
          </p>
          <div className="space-y-2">
            {actividades.map((act) => (
              <label key={act.actividad} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={seleccionadas.has(act.actividad)}
                  onChange={() => toggleActividad(act.actividad)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600"
                  data-testid={`actividad-checkbox-${act.actividad}`}
                />
                <span className="text-sm text-gray-800">{act.actividad}</span>
                <Badge variant={act.escala === 'numerica' ? 'info' : 'purple'}>
                  {act.escala}
                </Badge>
              </label>
            ))}
          </div>
          <Button
            variant="primary"
            onClick={handleConfirm}
            disabled={importar.isPending || seleccionadas.size === 0}
            isLoading={importar.isPending}
            data-testid="confirm-import"
          >
            {importar.isPending ? 'Importando…' : `Importar ${seleccionadas.size} actividad(es)`}
          </Button>
        </div>
      )}
    </div>
  )
}
