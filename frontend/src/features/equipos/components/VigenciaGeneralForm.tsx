/**
 * VigenciaGeneralForm — PATCH /equipos/vigencia-general form.
 * Task 1.9. < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useQuery } from '@tanstack/react-query'
import { useVigenciaGeneral } from '../hooks/equiposHooks'
import { Button } from '@/shared/components/ui'
import {
  listarTodasMaterias,
  listarTodosCohortes,
  listarTodasCarreras,
} from '@/features/monitores/services/monitoresService'

const schema = z.object({
  materia_id: z.string().min(1, 'Obligatorio'),
  carrera_id: z.string().min(1, 'Obligatorio'),
  cohorte_id: z.string().min(1, 'Obligatorio'),
  desde: z.string().min(1, 'Obligatorio'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'

export default function VigenciaGeneralForm() {
  const mutation = useVigenciaGeneral()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const materiasQuery = useQuery({ queryKey: ['admin-materias'], queryFn: listarTodasMaterias })
  const carrerasQuery = useQuery({ queryKey: ['admin-carreras'], queryFn: listarTodasCarreras })
  const cohortesQuery = useQuery({ queryKey: ['admin-cohortes'], queryFn: listarTodosCohortes })

  const materias = materiasQuery.data ?? []
  const carreras = carrerasQuery.data ?? []
  const cohortes = cohortesQuery.data ?? []

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
          <label className="block text-sm font-medium text-gray-700 mb-1">Materia</label>
          <select
            {...register('materia_id')}
            data-testid="vigencia-materia-id"
            className={inputClass}
            disabled={materiasQuery.isLoading}
          >
            <option value="">{materiasQuery.isLoading ? 'Cargando…' : '-- Seleccioná --'}</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
          {errors.materia_id && <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Carrera</label>
          <select
            {...register('carrera_id')}
            data-testid="vigencia-carrera-id"
            className={inputClass}
            disabled={carrerasQuery.isLoading}
          >
            <option value="">{carrerasQuery.isLoading ? 'Cargando…' : '-- Seleccioná --'}</option>
            {carreras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {errors.carrera_id && <p className="mt-1 text-xs text-red-600">{errors.carrera_id.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cohorte</label>
          <select
            {...register('cohorte_id')}
            data-testid="vigencia-cohorte-id"
            className={inputClass}
            disabled={cohortesQuery.isLoading}
          >
            <option value="">{cohortesQuery.isLoading ? 'Cargando…' : '-- Seleccioná --'}</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
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
      <Button
        type="submit"
        isLoading={mutation.isPending}
        disabled={mutation.isPending}
      >
        Actualizar vigencia
      </Button>
    </form>
  )
}
