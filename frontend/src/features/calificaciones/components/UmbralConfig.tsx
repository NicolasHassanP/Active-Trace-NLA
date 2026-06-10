/**
 * UmbralConfig — displays and edits the approval threshold for a materia.
 * GET /calificaciones/umbral on mount; PUT on form submit.
 * < 200 LOC.
 */
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useConfigurarUmbral, useUmbral } from '../hooks/calificacionesHooks'
import type { DomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'

interface Props {
  materia_id: string
}

export default function UmbralConfig({ materia_id }: Props) {
  const { data, isLoading, isError, error } = useUmbral(materia_id)
  const configurar = useConfigurarUmbral()

  const [umbralPct, setUmbralPct] = useState(60)
  const [valoresRaw, setValoresRaw] = useState('')

  // Sync form state when data loads
  useEffect(() => {
    if (data) {
      setUmbralPct(data.umbral_pct)
      setValoresRaw(data.valores_aprobatorios.join(', '))
    }
  }, [data])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const valores = valoresRaw
      .split(',')
      .map((v) => v.trim())
      .filter((v) => v.length > 0)

    configurar.mutate(
      { materia_id, umbral_pct: umbralPct, valores_aprobatorios: valores },
      {
        onSuccess: (result) => {
          toast.success(
            `Umbral guardado: ${result.umbral_pct}% — valores: ${result.valores_aprobatorios.join(', ') || '(ninguno)'}`,
          )
        },
        onError: (err) => {
          const de = err as unknown as DomainError
          toast.error(`Error al guardar umbral: ${de.detail}`)
        },
      },
    )
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando umbral…</p>
  }

  if (isError) {
    const de = error as unknown as DomainError
    return (
      <p role="alert" className="text-sm text-red-600">
        {de.detail ?? 'Error al cargar el umbral'}
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {data?.is_default && (
        <p className="text-xs text-gray-500 italic">
          Usando umbral por defecto del sistema. Podés personalizarlo a continuación.
        </p>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Umbral de aprobación (%)
        </label>
        <input
          type="number"
          min={0}
          max={100}
          value={umbralPct}
          onChange={(e) => setUmbralPct(Number(e.target.value))}
          className="w-32 border rounded px-3 py-2 text-sm"
          data-testid="umbral-pct-input"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Valores textuales aprobatorios (separados por coma)
        </label>
        <input
          type="text"
          value={valoresRaw}
          onChange={(e) => setValoresRaw(e.target.value)}
          placeholder="ej. Aprobado, Completado, Sí"
          className="w-full border rounded px-3 py-2 text-sm"
          data-testid="valores-aprobatorios-input"
        />
      </div>

      <Button
        type="submit"
        variant="primary"
        disabled={configurar.isPending}
        isLoading={configurar.isPending}
        data-testid="guardar-umbral"
      >
        {configurar.isPending ? 'Guardando…' : 'Guardar umbral'}
      </Button>
    </form>
  )
}
