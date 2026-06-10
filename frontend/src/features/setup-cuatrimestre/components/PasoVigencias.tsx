/**
 * PasoVigencias — Step 4: Update vigencias (desde/hasta) of team assignments.
 * Task 7.7. Reuses equiposService.vigenciaGeneral.
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { vigenciaGeneral } from '@/features/equipos/services/equiposService'
import { parseDomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'

const schema = z.object({
  materia_id: z.string().min(1, 'Materia obligatoria'),
  carrera_id: z.string().min(1, 'Carrera obligatoria'),
  cohorte_id: z.string().min(1, 'Cohorte obligatoria'),
  desde: z.string().min(1, 'Fecha desde obligatoria'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoVigencias({ onSuccess, onError }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormValues) {
    try {
      await vigenciaGeneral({
        materia_id: data.materia_id,
        carrera_id: data.carrera_id,
        cohorte_id: data.cohorte_id,
        desde: data.desde,
        hasta: data.hasta || null,
      })
      onSuccess()
    } catch (err) {
      const de = parseDomainError(err)
      onError(de.detail)
    }
  }

  const inputClass =
    'mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-vigencias">
      <p className="text-sm text-gray-600">
        Actualizá las fechas de vigencia para todas las asignaciones activas del equipo.
      </p>

      <div className="grid grid-cols-3 gap-3">
        {(['materia_id', 'carrera_id', 'cohorte_id'] as const).map((field) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700">
              {field.replace('_id', '').charAt(0).toUpperCase() +
                field.replace('_id', '').slice(1)}
            </label>
            <input {...register(field)} className={inputClass} />
            {errors[field] && (
              <p className="mt-1 text-xs text-red-600">{errors[field]?.message}</p>
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Desde</label>
          <input {...register('desde')} type="date" className={inputClass} />
          {errors.desde && <p className="mt-1 text-xs text-red-600">{errors.desde.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Hasta (opcional)</label>
          <input {...register('hasta')} type="date" className={inputClass} />
        </div>
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
        {isSubmitting ? 'Actualizando…' : 'Actualizar vigencias'}
      </Button>
    </form>
  )
}
