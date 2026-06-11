/**
 * PasoClonarEquipo — Step 2: Clone docente team from a previous cohorte.
 * Task 7.5. Reuses equiposService.clonarEquipo.
 * origen_{materia,carrera,cohorte}_id and destino_{materia,carrera,cohorte}_id
 * → 6 explicit <select> by nombre (useEstructuraOptions, same lists for both groups).
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { clonarEquipo } from '@/features/equipos/services/equiposService'
import { parseDomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'
import { useEstructuraOptions } from '../hooks/useEstructuraOptions'

const schema = z.object({
  origen_materia_id: z.string().min(1, 'Materia origen obligatorio'),
  origen_carrera_id: z.string().min(1, 'Carrera origen obligatorio'),
  origen_cohorte_id: z.string().min(1, 'Cohorte origen obligatorio'),
  destino_materia_id: z.string().min(1, 'Materia destino obligatorio'),
  destino_carrera_id: z.string().min(1, 'Carrera destino obligatorio'),
  destino_cohorte_id: z.string().min(1, 'Cohorte destino obligatorio'),
  desde: z.string().min(1, 'Fecha desde obligatoria'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoClonarEquipo({ onSuccess, onError }: Props) {
  const { materias, carreras, cohortes, isLoading } = useEstructuraOptions()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormValues) {
    try {
      await clonarEquipo({
        origen_materia_id: data.origen_materia_id,
        origen_carrera_id: data.origen_carrera_id,
        origen_cohorte_id: data.origen_cohorte_id,
        destino_materia_id: data.destino_materia_id,
        destino_carrera_id: data.destino_carrera_id,
        destino_cohorte_id: data.destino_cohorte_id,
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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-clonar-equipo">
      <p className="text-sm text-gray-600">
        Indicá la tripleta de origen (cuatrimestre anterior) y la de destino (nuevo cuatrimestre).
      </p>

      {/* Origen */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Materia origen</label>
          <select
            {...register('origen_materia_id')}
            className={inputClass}
            data-testid="clonar-origen-materia-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>{m.nombre}</option>
            ))}
          </select>
          {errors.origen_materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.origen_materia_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Carrera origen</label>
          <select
            {...register('origen_carrera_id')}
            className={inputClass}
            data-testid="clonar-origen-carrera-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {carreras.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.origen_carrera_id && (
            <p className="mt-1 text-xs text-red-600">{errors.origen_carrera_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Cohorte origen</label>
          <select
            {...register('origen_cohorte_id')}
            className={inputClass}
            data-testid="clonar-origen-cohorte-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.origen_cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.origen_cohorte_id.message}</p>
          )}
        </div>
      </div>

      {/* Destino */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Materia destino</label>
          <select
            {...register('destino_materia_id')}
            className={inputClass}
            data-testid="clonar-destino-materia-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>{m.nombre}</option>
            ))}
          </select>
          {errors.destino_materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.destino_materia_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Carrera destino</label>
          <select
            {...register('destino_carrera_id')}
            className={inputClass}
            data-testid="clonar-destino-carrera-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {carreras.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.destino_carrera_id && (
            <p className="mt-1 text-xs text-red-600">{errors.destino_carrera_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Cohorte destino</label>
          <select
            {...register('destino_cohorte_id')}
            className={inputClass}
            data-testid="clonar-destino-cohorte-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.destino_cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.destino_cohorte_id.message}</p>
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
        {isSubmitting ? 'Clonando…' : 'Clonar equipo'}
      </Button>
    </form>
  )
}
