/**
 * PasoVigencias — Step 4: Update vigencias (desde/hasta) of team assignments.
 * Task 7.7. Reuses equiposService.vigenciaGeneral.
 * materia_id / carrera_id / cohorte_id → <select> by nombre (useEstructuraOptions).
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { vigenciaGeneral } from '@/features/equipos/services/equiposService'
import { parseDomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'
import { useEstructuraOptions } from '../hooks/useEstructuraOptions'

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
  const { materias, carreras, cohortes, isLoading } = useEstructuraOptions()

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

  const placeholder = isLoading ? 'Cargando…' : '-- Seleccioná --'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-vigencias">
      <p className="text-sm text-gray-600">
        Actualizá las fechas de vigencia para todas las asignaciones activas del equipo.
      </p>

      <div className="grid grid-cols-3 gap-3">
        {/* Materia — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Materia</label>
          <select
            {...register('materia_id')}
            className={inputClass}
            data-testid="vigencias-materia-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>{m.nombre}</option>
            ))}
          </select>
          {errors.materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>
          )}
        </div>

        {/* Carrera — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Carrera</label>
          <select
            {...register('carrera_id')}
            className={inputClass}
            data-testid="vigencias-carrera-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {carreras.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.carrera_id && (
            <p className="mt-1 text-xs text-red-600">{errors.carrera_id.message}</p>
          )}
        </div>

        {/* Cohorte — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Cohorte</label>
          <select
            {...register('cohorte_id')}
            className={inputClass}
            data-testid="vigencias-cohorte-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>
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
