/**
 * AsignacionMasivaForm — React Hook Form + Zod form for POST /equipos/asignacion-masiva.
 * Task 1.9. < 200 LOC.
 *
 * UX improvements:
 *  - usuario_ids: UsuarioMultiCombobox (replaces raw UUID textarea)
 *  - materia_id:  <select> by nombre (from GET /admin/materias)
 *  - cohorte_id:  <select> by nombre (from GET /admin/cohortes)
 *  - carrera_id:  raw UUID input (TODO: select when /admin/carreras endpoint exists)
 */
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useQuery } from '@tanstack/react-query'
import { useAsignacionMasiva } from '../hooks/equiposHooks'
import type { RolAsignacion } from '../types'
import { Button } from '@/shared/components/ui'
import UsuarioMultiCombobox from '@/features/asignaciones/components/UsuarioMultiCombobox'
import { listarTodasMaterias, listarTodosCohortes } from '@/features/monitores/services/monitoresService'

const schema = z.object({
  usuario_ids: z.array(z.string().uuid()).min(1, 'Seleccioná al menos un usuario'),
  materia_id: z.string().min(1, 'Obligatorio'),
  carrera_id: z.string().min(1, 'Obligatorio'),
  cohorte_id: z.string().min(1, 'Obligatorio'),
  rol: z.enum(['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']),
  desde: z.string().min(1, 'Obligatorio'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const ROL_OPTIONS: RolAsignacion[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'

export default function AsignacionMasivaForm() {
  const mutation = useAsignacionMasiva()

  const materiasQuery = useQuery({
    queryKey: ['admin-materias'],
    queryFn: listarTodasMaterias,
  })

  const cohortesQuery = useQuery({
    queryKey: ['admin-cohortes'],
    queryFn: listarTodosCohortes,
  })

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { rol: 'PROFESOR', usuario_ids: [] },
  })

  function onSubmit(values: FormValues) {
    mutation.mutate(
      {
        usuario_ids: values.usuario_ids,
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

  const materias = materiasQuery.data ?? []
  const cohortes = cohortesQuery.data ?? []

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <h3 className="font-medium text-gray-800">Asignación masiva</h3>

      {/* Usuarios — multi-select combobox */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Usuarios
        </label>
        <Controller
          name="usuario_ids"
          control={control}
          render={({ field }) => (
            <UsuarioMultiCombobox
              value={field.value}
              onChange={field.onChange}
              error={errors.usuario_ids?.message}
            />
          )}
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        {/* Materia — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Materia</label>
          <select
            {...register('materia_id')}
            className={inputClass}
            data-testid="masiva-materia-id"
            disabled={materiasQuery.isLoading}
          >
            <option value="">
              {materiasQuery.isLoading ? 'Cargando…' : '-- Seleccioná --'}
            </option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
          {errors.materia_id && <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>}
        </div>

        {/* Carrera — TODO: select when /admin/carreras endpoint exists */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Carrera ID</label>
          {/* TODO: replace with <select> when GET /admin/carreras endpoint is implemented */}
          <input
            {...register('carrera_id')}
            className={inputClass}
            data-testid="masiva-carrera-id"
            placeholder="UUID de carrera"
          />
          {errors.carrera_id && <p className="mt-1 text-xs text-red-600">{errors.carrera_id.message}</p>}
        </div>

        {/* Cohorte — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cohorte</label>
          <select
            {...register('cohorte_id')}
            className={inputClass}
            data-testid="masiva-cohorte-id"
            disabled={cohortesQuery.isLoading}
          >
            <option value="">
              {cohortesQuery.isLoading ? 'Cargando…' : '-- Seleccioná --'}
            </option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {errors.cohorte_id && <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
          <select {...register('rol')} className={inputClass}>
            {ROL_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
          <input type="date" {...register('desde')} className={inputClass} />
          {errors.desde && <p className="mt-1 text-xs text-red-600">{errors.desde.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Hasta (opcional)</label>
          <input type="date" {...register('hasta')} className={inputClass} />
        </div>
      </div>

      <Button
        type="submit"
        isLoading={mutation.isPending}
        disabled={mutation.isPending}
      >
        Asignar
      </Button>
    </form>
  )
}
