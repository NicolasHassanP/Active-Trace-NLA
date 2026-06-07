/**
 * PadronImportForm — upload → preview rows → confirm.
 * 422 from preview shown inline. < 200 LOC.
 */
import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { usePreviewPadron, useActivarPadron } from '../hooks/padronHooks'
import type { DomainError } from '@/shared/services/domainError'
import type { PadronRowDTO } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  materia_id: string
  cohorte_id: string
  onSuccess?: (totalFilas: number) => void
}

export default function PadronImportForm({ materia_id, cohorte_id, onSuccess }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [previewRows, setPreviewRows] = useState<PadronRowDTO[] | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const preview = usePreviewPadron()
  const activar = useActivarPadron()

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setPreviewError(null)
    setPreviewRows(null)
    preview.mutate(file, {
      onSuccess: (rows) => setPreviewRows(rows),
      onError: (err) => {
        const de = err as DomainError
        setPreviewError(de.detail ?? 'Error al previsualizar el archivo')
      },
    })
  }

  function handleConfirm() {
    if (!previewRows) return
    activar.mutate(
      { materia_id, cohorte_id, rows: previewRows },
      {
        onSuccess: (version) => {
          toast.success(`Padrón activado: ${version.filas_total} filas importadas`)
          setPreviewRows(null)
          if (fileRef.current) fileRef.current.value = ''
          onSuccess?.(version.filas_total)
        },
        onError: (err) => {
          const de = err as DomainError
          toast.error(`Error al activar: ${de.detail}`)
        },
      },
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Archivo de padrón (.xlsx o .csv)
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.csv"
          onChange={handleFileChange}
          disabled={preview.isPending}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          data-testid="padron-file-input"
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

      {previewRows && previewRows.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            Se detectaron <strong>{previewRows.length}</strong> filas. Revisá y confirmá la importación.
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs border">
              <thead className="bg-gray-50">
                <tr>
                  {['Nombre', 'Apellidos', 'Email', 'Comisión', 'Regional'].map((h) => (
                    <th key={h} className="px-2 py-1 text-left font-medium text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.slice(0, 10).map((row, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">{row.nombre}</td>
                    <td className="px-2 py-1">{row.apellidos}</td>
                    <td className="px-2 py-1">{row.email}</td>
                    <td className="px-2 py-1">{row.comision}</td>
                    <td className="px-2 py-1">{row.regional}</td>
                  </tr>
                ))}
                {previewRows.length > 10 && (
                  <tr>
                    <td colSpan={5} className="px-2 py-1 text-gray-400 italic">
                      …y {previewRows.length - 10} filas más
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Button
            onClick={handleConfirm}
            isLoading={activar.isPending}
            disabled={activar.isPending}
            data-testid="confirm-import"
          >
            Confirmar importación
          </Button>
        </div>
      )}
    </div>
  )
}
