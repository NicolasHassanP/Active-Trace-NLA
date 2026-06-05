/**
 * EquipoFilters — query form for GET /api/v1/equipos (tripleta + optional filters).
 * Uses React Hook Form + Zod. Task 1.9. < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { EquipoQueryParams, RolAsignacion } from '../types'

const schema = z.object({
  materia_id: z.string().min(1, 'Materia obligatoria'),
  carrera_id: z.string().min(1, 'Carrera obligatoria'),
  cohorte_id: z.string().min(1, 'Cohorte obligatoria'),
  rol: z.string().optional(),
  responsable_id: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSearch: (params: EquipoQueryParams) => void
}

const ROL_OPTIONS: RolAsignacion[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']

export default function EquipoFilters({ onSearch }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  function onSubmit(values: FormValues) {
    onSearch({
      materia_id: values.materia_id,
      carrera_id: values.carrera_id,
      cohorte_id: values.cohorte_id,
      rol: (values.rol as RolAsignacion) || undefined,
      responsable_id: values.responsable_id || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-2 gap-4 md:grid-cols-3">
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
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Rol (opcional)</label>
        <select {...register('rol')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
          <option value="">Todos</option>
          {ROL_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Responsable ID (opcional)</label>
        <input {...register('responsable_id')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
      </div>
      <div className="flex items-end">
        <button type="submit" className="w-full rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700">
          Consultar equipo
        </button>
      </div>
    </form>
  )
}
