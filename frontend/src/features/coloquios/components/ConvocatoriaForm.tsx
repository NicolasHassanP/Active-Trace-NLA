/**
 * ConvocatoriaForm — RHF + Zod form for creating a convocatoria.
 * Task 6.10. < 200 LOC. Tailwind only.
 * Materia and Cohorte are populated via select dropdowns from catalog hooks
 * (useEstructuraOptions) — no raw UUID input exposed to the user.
 */
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { convocatoriaSchema, type ConvocatoriaFormValues } from '../services/convocatoriaSchema'
import { Button } from '@/shared/components/ui'
import { useEstructuraOptions } from '@/features/setup-cuatrimestre/hooks/useEstructuraOptions'

interface Props {
  onSubmit: (values: ConvocatoriaFormValues) => void
  isLoading?: boolean
}

export default function ConvocatoriaForm({ onSubmit, isLoading = false }: Props) {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<ConvocatoriaFormValues>({
    resolver: zodResolver(convocatoriaSchema),
    defaultValues: {
      tipo: 'Coloquio',
      dias_disponibles: 1,
      turnos: [{ fecha: '', cupo_total: 1, franja: null }],
    },
  })

  const { materias, cohortes, isLoading: catalogLoading } = useEstructuraOptions()
  // The catalog doesn't expose materia→carrera mapping so all cohortes are
  // shown; backend enforces the carrera constraint on submit.

  return (
    <form
      data-testid="convocatoria-form"
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="materia_id">
            Materia
          </label>
          <Controller
            name="materia_id"
            control={control}
            render={({ field }) => (
              <select
                id="materia_id"
                {...field}
                disabled={catalogLoading}
                className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
              >
                <option value="">
                  {catalogLoading ? 'Cargando…' : '-- Seleccioná una materia --'}
                </option>
                {materias.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </select>
            )}
          />
          {errors.materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="cohorte_id">
            Cohorte
          </label>
          <Controller
            name="cohorte_id"
            control={control}
            render={({ field }) => (
              <select
                id="cohorte_id"
                {...field}
                disabled={catalogLoading}
                className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
              >
                <option value="">
                  {catalogLoading ? 'Cargando…' : '-- Seleccioná una cohorte --'}
                </option>
                {cohortes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            )}
          />
          {errors.cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="tipo">
            Tipo
          </label>
          <select
            id="tipo"
            {...register('tipo')}
            className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
          >
            <option value="Coloquio">Coloquio</option>
            <option value="TP">TP</option>
            <option value="Parcial">Parcial</option>
            <option value="Recuperatorio">Recuperatorio</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="instancia">
            Instancia
          </label>
          <input
            id="instancia"
            type="text"
            {...register('instancia')}
            className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
            placeholder="Primera, Segunda, etc."
          />
          {errors.instancia && (
            <p className="mt-1 text-xs text-red-600">{errors.instancia.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="dias_disponibles">
            Días disponibles
          </label>
          <input
            id="dias_disponibles"
            type="number"
            min={1}
            {...register('dias_disponibles', { valueAsNumber: true })}
            className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
          />
          {errors.dias_disponibles && (
            <p className="mt-1 text-xs text-red-600">{errors.dias_disponibles.message}</p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium text-gray-700">Turnos</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-600" htmlFor="turno-fecha">
              Fecha
            </label>
            <input
              id="turno-fecha"
              type="date"
              {...register('turnos.0.fecha')}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600" htmlFor="turno-cupo">
              Cupo total
            </label>
            <input
              id="turno-cupo"
              type="number"
              min={1}
              {...register('turnos.0.cupo_total', { valueAsNumber: true })}
              className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
            />
            {errors.turnos?.[0]?.cupo_total && (
              <p className="mt-1 text-xs text-red-600">{errors.turnos[0].cupo_total.message}</p>
            )}
          </div>
        </div>
        {errors.turnos?.root && (
          <p className="text-xs text-red-600">{errors.turnos.root.message}</p>
        )}
      </div>

      <div className="flex justify-end pt-2">
        <Button type="submit" variant="primary" disabled={isLoading} isLoading={isLoading}>
          {isLoading ? 'Creando…' : 'Crear convocatoria'}
        </Button>
      </div>
    </form>
  )
}
