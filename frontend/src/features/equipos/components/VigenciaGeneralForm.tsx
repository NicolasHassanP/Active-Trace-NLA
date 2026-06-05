/**
 * VigenciaGeneralForm — PATCH /equipos/vigencia-general form.
 * Task 1.9. < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useVigenciaGeneral } from '../hooks/equiposHooks'

const schema = z.object({
  materia_id: z.string().min(1, 'Obligatorio'),
  carrera_id: z.string().min(1, 'Obligatorio'),
  cohorte_id: z.string().min(1, 'Obligatorio'),
  desde: z.string().min(1, 'Obligatorio'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

export default function VigenciaGeneralForm() {
  const mutation = useVigenciaGeneral()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  function onSubmit(values: FormValues) {
    mutation.mutate(
      { ...values, hasta: values.hasta || null },
      {
        onSuccess: (data) => {
          toast.success(`${data.afectadas} asignaciones actualizadas`)
          reset()
        },
        onError: (err) => {
          toast.error((err as { detail?: string }).detail ?? 'Error al actualizar vigencia')
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <h3 className="font-medium text-gray-800">Vigencia general del equipo</h3>
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
      <div className="grid grid-cols-2 gap-3">
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
        {mutation.isPending ? 'Actualizando…' : 'Actualizar vigencia'}
      </button>
    </form>
  )
}
