/**
 * ComposeComunicacion — RHF+Zod form for composing a communication batch.
 * OQ-4: variables_por_destinatario are built automatically from AlumnoAtrasado — read-only.
 * < 200 LOC.
 */
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { usePreviewComunicacion, useEncolarLote } from '../hooks/comunicacionHooks'
import type { DomainError } from '@/shared/services/domainError'
import type { AlumnoAtrasado } from '@/features/atrasados/types'
import type { PreviewResponse } from '../types'
import { Button } from '@/shared/components/ui'

const schema = z.object({
  asunto_plantilla: z.string().min(1, 'El asunto es requerido'),
  cuerpo_plantilla: z.string().min(1, 'El cuerpo es requerido'),
})
type FormValues = z.infer<typeof schema>

interface Props {
  destinatarios: AlumnoAtrasado[]
  onEncolado?: (loteId: string) => void
}

/** Builds variables map from AlumnoAtrasado for a single recipient */
function buildVariables(alumno: AlumnoAtrasado): Record<string, string> {
  return {
    nombre: alumno.nombre,
    apellidos: alumno.apellidos,
    email: alumno.email,
    actividades_faltantes: alumno.actividades_faltantes.join(', '),
    actividades_no_aprobadas: alumno.actividades_no_aprobadas.join(', '),
  }
}

export default function ComposeComunicacion({ destinatarios, onEncolado }: Props) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const preview = usePreviewComunicacion()
  const encolar = useEncolarLote()
  const [previewResult, setPreviewResult] = useState<PreviewResponse | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const asunto = watch('asunto_plantilla')
  const cuerpo = watch('cuerpo_plantilla')

  // Reset preview when template changes
  useEffect(() => {
    setPreviewResult(null)
    setPreviewError(null)
  }, [asunto, cuerpo])

  function handlePreview() {
    if (!destinatarios[0]) {
      setPreviewError('No hay destinatarios para previsualizar')
      return
    }
    setPreviewError(null)
    preview.mutate(
      { asunto_plantilla: asunto, cuerpo_plantilla: cuerpo, variables: buildVariables(destinatarios[0]) },
      {
        onSuccess: (r) => setPreviewResult(r),
        onError: (err) => {
          const de = err as DomainError
          setPreviewError(de.detail ?? 'Error al previsualizar')
          setPreviewResult(null)
        },
      },
    )
  }

  function onSubmit(values: FormValues) {
    if (destinatarios.length === 0) return
    // 422 blocks enqueue: ensure no preview error before submitting
    if (previewError) return
    encolar.mutate(
      {
        destinatarios: destinatarios.map((a) => a.email),
        asunto_plantilla: values.asunto_plantilla,
        cuerpo_plantilla: values.cuerpo_plantilla,
        variables_por_destinatario: Object.fromEntries(
          destinatarios.map((a) => [a.email, buildVariables(a)]),
        ),
      },
      {
        onSuccess: (res) => { onEncolado?.(res.lote_id) },
        onError: (err) => {
          const de = err as DomainError
          setPreviewError(de.detail ?? 'Error al encolar')
        },
      },
    )
  }

  const canEncolar = !previewError && destinatarios.length > 0

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="compose-form">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Asunto</label>
        <input
          {...register('asunto_plantilla')}
          placeholder="Hola {{nombre}}"
          className="w-full border rounded px-3 py-2 text-sm"
          data-testid="asunto-input"
        />
        {errors.asunto_plantilla && (
          <p className="text-xs text-red-600 mt-1">{errors.asunto_plantilla.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Cuerpo</label>
        <textarea
          {...register('cuerpo_plantilla')}
          rows={5}
          placeholder="Estimado {{nombre}}, te contactamos porque…"
          className="w-full border rounded px-3 py-2 text-sm"
          data-testid="cuerpo-input"
        />
        {errors.cuerpo_plantilla && (
          <p className="text-xs text-red-600 mt-1">{errors.cuerpo_plantilla.message}</p>
        )}
      </div>

      {/* Destinatarios — read-only list of recipients */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-1">
          Destinatarios ({destinatarios.length})
        </p>
        <div className="text-xs text-gray-500">
          {destinatarios.map((d) => d.email).join(', ')}
        </div>
      </div>

      {previewError && (
        <div role="alert" className="text-sm text-red-600 p-2 bg-red-50 rounded" data-testid="preview-error">
          {previewError}
        </div>
      )}

      {previewResult && (
        <div className="p-3 bg-gray-50 border rounded space-y-1 text-sm" data-testid="preview-result">
          <p><strong>Asunto:</strong> {previewResult.asunto}</p>
          <p><strong>Cuerpo:</strong> {previewResult.cuerpo}</p>
        </div>
      )}

      <div className="flex gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={handlePreview}
          isLoading={preview.isPending}
          disabled={preview.isPending || destinatarios.length === 0}
          data-testid="preview-btn"
        >
          Previsualizar
        </Button>
        <Button
          type="submit"
          isLoading={encolar.isPending}
          disabled={!canEncolar || encolar.isPending}
          data-testid="encolar-btn"
        >
          Encolar
        </Button>
      </div>
    </form>
  )
}
