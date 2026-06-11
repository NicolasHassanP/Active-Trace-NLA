/**
 * PasoAsignaciones — Step 3: Bulk assignment adjustments.
 * Task 7.6. Reuses equiposService.asignacionMasiva.
 * usuario_ids → UsuarioMultiCombobox (Controller).
 * materia_id / carrera_id / cohorte_id → <select> by nombre (useEstructuraOptions).
 * < 200 LOC.
 */
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { asignacionMasiva } from '@/features/equipos/services/equiposService'
import { parseDomainError } from '@/shared/services/domainError'
import type { RolAsignacion } from '@/features/equipos/types'
import { Button } from '@/shared/components/ui'
import UsuarioMultiCombobox from '@/features/asignaciones/components/UsuarioMultiCombobox'
import { useEstructuraOptions } from '../hooks/useEstructuraOptions'

const ROL_OPTIONS: RolAsignacion[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO']

const schema = z.object({
  usuario_ids: z.array(z.string().uuid()).min(1, 'Seleccioná al menos un usuario'),
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
  const { materias, carreras, cohortes, isLoading } = useEstructuraOptions()

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { usuario_ids: [] },
  })

  async function onSubmit(data: FormValues) {
    try {
      await asignacionMasiva({
        usuario_ids: data.usuario_ids,
        materia_id: data.materia_id,
        carrera_id: data.carrera_id,
        cohorte_id: data.cohorte_id,
        rol: data.rol,
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
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
      data-testid="paso-asignaciones"
    >
      <p className="text-sm text-gray-600">
        Realizá asignaciones masivas de docentes al nuevo cuatrimestre.
      </p>

      {/* Usuarios — multi-select combobox */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Usuarios</label>
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
          <label className="block text-sm font-medium text-gray-700">Materia</label>
          <select
            {...register('materia_id')}
            className={inputClass}
            data-testid="asignaciones-materia-id"
            disabled={isLoading}
          >
            <option value="">
              {isLoading ? 'Cargando…' : '-- Seleccioná --'}
            </option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
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
            data-testid="asignaciones-carrera-id"
            disabled={isLoading}
          >
            <option value="">
              {isLoading ? 'Cargando…' : '-- Seleccioná --'}
            </option>
            {carreras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
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
            data-testid="asignaciones-cohorte-id"
            disabled={isLoading}
          >
            <option value="">
              {isLoading ? 'Cargando…' : '-- Seleccioná --'}
            </option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {errors.cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>
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

      <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
        {isSubmitting ? 'Asignando…' : 'Aplicar asignaciones'}
      </Button>
    </form>
  )
}
