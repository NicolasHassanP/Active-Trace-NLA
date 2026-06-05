/**
 * AsignacionMasivaForm — React Hook Form + Zod form for POST /equipos/asignacion-masiva.
 * Task 1.9. < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useAsignacionMasiva } from '../hooks/equiposHooks'
import type { RolAsignacion } from '../types'

const schema = z.object({
  usuario_ids_raw: z.string().min(1, 'Ingresá al menos un usuario ID'),
  materia_id: z.string().min(1, 'Obligatorio'),
  carrera_id: z.string().min(1, 'Obligatorio'),
  cohorte_id: z.string().min(1, 'Obligatorio'),
  rol: z.enum(['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']),
  desde: z.string().min(1, 'Obligatorio'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const ROL_OPTIONS: RolAsignacion[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']

export default function AsignacionMasivaForm() {
  const mutation = useAsignacionMasiva()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { rol: 'PROFESOR' } })

  function onSubmit(values: FormValues) {
    const usuario_ids = values.usuario_ids_raw.split(',').map((s) => s.trim()).filter(Boolean)
    mutation.mutate(
      {
        usuario_ids,
        materia_id: values.materia_id,
        carrera_id: values.carrera_id,
        cohorte_id: values.cohorte_id,
        rol: values.rol,
        desde: values.desde,
        hasta: values.hasta || null,
      },
      {
        onSuccess: (data) => {
          toast.success(`${data.creadas} asignaciones creadas`)
          reset()
        },
        onError: (err) => {
          const detail = (err as { detail?: string }).detail ?? 'Error al asignar'
          toast.error(detail)
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <h3 className="font-medium text-gray-800">Asignación masiva</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Usuario IDs (separados por coma)
        </label>
        <input {...register('usuario_ids_raw')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        {errors.usuario_ids_raw && <p className="mt-1 text-xs text-red-600">{errors.usuario_ids_raw.message}</p>}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Materia ID</label>
          <input {...register('materia_id')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.materia_id && <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Carrera ID</label>
          <input {...register('carrera_id')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.carrera_id && <p className="mt-1 text-xs text-red-600">{errors.carrera_id.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cohorte ID</label>
          <input {...register('cohorte_id')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.cohorte_id && <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
          <select {...register('rol')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
            {ROL_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
          <input type="date" {...register('desde')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.desde && <p className="mt-1 text-xs text-red-600">{errors.desde.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Hasta (opcional)</label>
          <input type="date" {...register('hasta')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        </div>
      </div>

      <button
        type="submit"
        disabled={mutation.isPending}
        className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {mutation.isPending ? 'Asignando…' : 'Asignar'}
      </button>
    </form>
  )
}
