/**
 * PasoAsignaciones — Step 3: Bulk assignment adjustments.
 * Task 7.6. Reuses equiposService.asignacionMasiva.
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { asignacionMasiva } from '@/features/equipos/services/equiposService'
import { parseDomainError } from '@/shared/services/domainError'
import type { RolAsignacion } from '@/features/equipos/types'

const ROL_OPTIONS: RolAsignacion[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']

const schema = z.object({
  usuario_ids: z
    .string()
    .min(1, 'Al menos un usuario ID obligatorio')
    .transform((v) => v.split(',').map((s) => s.trim()).filter(Boolean)),
  materia_id: z.string().min(1, 'Materia obligatoria'),
  carrera_id: z.string().min(1, 'Carrera obligatoria'),
  cohorte_id: z.string().min(1, 'Cohorte obligatoria'),
  rol: z.enum(['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']),
  desde: z.string().min(1, 'Fecha desde obligatoria'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoAsignaciones({ onSuccess, onError }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormValues) {
    try {
      await asignacionMasiva({
        usuario_ids: data.usuario_ids,
        materia_id: data.materia_id,
        carrera_id: data.carrera_id,
        cohorte_id: data.cohorte_id,
        rol: data.rol,
        desde: data.desde,
        hasta: data.hasta ?? null,
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
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
      data-testid="paso-asignaciones"
    >
      <p className="text-sm text-gray-600">
        Realizá asignaciones masivas de docentes al nuevo cuatrimestre.
      </p>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          IDs de usuarios (separados por coma)
        </label>
        <input {...register('usuario_ids')} className={inputClass} placeholder="uuid1, uuid2" />
        {errors.usuario_ids && (
          <p className="mt-1 text-xs text-red-600">{errors.usuario_ids.message}</p>
        )}
      </div>

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

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Rol</label>
          <select {...register('rol')} className={inputClass}>
            {ROL_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          {errors.rol && <p className="mt-1 text-xs text-red-600">{errors.rol.message}</p>}
        </div>
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

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Asignando…' : 'Aplicar asignaciones'}
      </button>
    </form>
  )
}
