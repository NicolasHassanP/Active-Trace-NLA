/**
 * UmbralConfigDefault — configure the default approval threshold for a materia/cohorte.
 * Used by ADMIN (scope global). Sets asignacion_id=None (default) in the backend.
 * < 200 LOC.
 */
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useConfigurarUmbralDefault, useUmbralDefault } from '../hooks/calificacionesHooks'
import type { DomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'

interface Props {
  materia_id: string
  cohorte_id?: string
}

export default function UmbralConfigDefault({ materia_id, cohorte_id }: Props) {
  const { data, isLoading, isError, error } = useUmbralDefault(materia_id, cohorte_id)
  const configurar = useConfigurarUmbralDefault()

  const [umbralPct, setUmbralPct] = useState(60)
  const [valoresRaw, setValoresRaw] = useState('')

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
      {
        materia_id,
        umbral_pct: umbralPct,
        valores_aprobatorios: valores,
        cohorte_id: cohorte_id ?? null,
      },
      {
        onSuccess: (result) => {
          toast.success(
            `Umbral por defecto guardado: ${result.umbral_pct}% — valores: ${result.valores_aprobatorios.join(', ') || '(ninguno)'}`,
          )
        },
        onError: (err) => {
          const de = err as unknown as DomainError
          toast.error(`Error al guardar umbral por defecto: ${de.detail}`)
        },
      },
    )
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando umbral por defecto…</p>
  }

  if (isError) {
    const de = error as unknown as DomainError
    return (
      <p role="alert" className="text-sm text-red-600">
        {de.detail ?? 'Error al cargar el umbral por defecto'}
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded px-3 py-2 text-sm text-blue-800">
        <strong>Umbral por defecto (materia/cohorte)</strong>
        <p className="text-xs mt-1">
          Este umbral aplica como valor predeterminado para todos los docentes de esta materia
          {cohorte_id ? ' en la cohorte seleccionada' : ''}. Cada docente puede configurar su propio override.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Umbral de aprobación por defecto (%)
        </label>
        <input
          type="number"
          min={0}
          max={100}
          value={umbralPct}
          onChange={(e) => setUmbralPct(Number(e.target.value))}
          className="w-32 border rounded px-3 py-2 text-sm"
          data-testid="umbral-default-pct-input"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Valores textuales aprobatorios por defecto (separados por coma)
        </label>
        <input
          type="text"
          value={valoresRaw}
          onChange={(e) => setValoresRaw(e.target.value)}
          placeholder="ej. Aprobado, Completado, Sí"
          className="w-full border rounded px-3 py-2 text-sm"
          data-testid="umbral-default-valores-input"
        />
      </div>

      <Button
        type="submit"
        variant="primary"
        disabled={configurar.isPending}
        isLoading={configurar.isPending}
        data-testid="guardar-umbral-default"
      >
        {configurar.isPending ? 'Guardando…' : 'Guardar umbral por defecto'}
      </Button>
    </form>
  )
}
