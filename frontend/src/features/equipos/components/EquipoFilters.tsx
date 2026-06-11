/**
 * EquipoFilters — query form for GET /api/v1/equipos (tripleta + optional filters).
 * Uses React Hook Form + Zod. Task 1.9. < 200 LOC.
 *
 * UX: materia/carrera/cohorte are <select> by nombre (from /admin/*),
 * responsable is a UsuarioCombobox (search by name). No raw UUIDs.
 */
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery } from '@tanstack/react-query'
import type { EquipoQueryParams, RolAsignacion } from '../types'
import { Button } from '@/shared/components/ui'
import UsuarioCombobox from '@/features/asignaciones/components/UsuarioCombobox'
import {
  listarTodasMaterias,
  listarTodosCohortes,
  listarTodasCarreras,
} from '@/features/monitores/services/monitoresService'

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

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'

export default function EquipoFilters({ onSearch }: Props) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const materiasQuery = useQuery({ queryKey: ['admin-materias'], queryFn: listarTodasMaterias })
  const carrerasQuery = useQuery({ queryKey: ['admin-carreras'], queryFn: listarTodasCarreras })
  const cohortesQuery = useQuery({ queryKey: ['admin-cohortes'], queryFn: listarTodosCohortes })

  const materias = materiasQuery.data ?? []
  const carreras = carrerasQuery.data ?? []
  const cohortes = cohortesQuery.data ?? []

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
        <label className="block text-sm font-medium text-gray-700 mb-1">Materia</label>
        <select
          {...register('materia_id')}
          data-testid="equipo-materia-id"
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
          data-testid="equipo-carrera-id"
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
          data-testid="equipo-cohorte-id"
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
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Rol (opcional)</label>
        <select {...register('rol')} className={inputClass}>
          <option value="">Todos</option>
          {ROL_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Responsable (opcional)</label>
        <Controller
          name="responsable_id"
          control={control}
          render={({ field }) => (
            <UsuarioCombobox
              value={field.value || null}
              onChange={(id) => field.onChange(id ?? '')}
              error={errors.responsable_id?.message}
            />
          )}
        />
      </div>
      <div className="flex items-end">
        <Button type="submit" className="w-full">
          Consultar equipo
        </Button>
      </div>
    </form>
  )
}
