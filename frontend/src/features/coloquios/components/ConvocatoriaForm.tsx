/**
 * ConvocatoriaForm — RHF + Zod form for creating a convocatoria.
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { convocatoriaSchema, type ConvocatoriaFormValues } from '../services/convocatoriaSchema'
import { Button } from '@/shared/components/ui'

interface Props {
  onSubmit: (values: ConvocatoriaFormValues) => void
  isLoading?: boolean
}

export default function ConvocatoriaForm({ onSubmit, isLoading = false }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ConvocatoriaFormValues>({
    resolver: zodResolver(convocatoriaSchema),
    defaultValues: {
      tipo: 'Coloquio',
      dias_disponibles: 1,
      turnos: [{ fecha: '', cupo_total: 1, franja: null }],
    },
  })

  return (
    <form
      data-testid="convocatoria-form"
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="materia_id">
            Materia ID
          </label>
          <input
            id="materia_id"
            type="text"
            {...register('materia_id')}
            className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
            placeholder="UUID de la materia"
          />
          {errors.materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700" htmlFor="cohorte_id">
            Cohorte ID
          </label>
          <input
            id="cohorte_id"
            type="text"
            {...register('cohorte_id')}
            className="mt-1 block w-full rounded border-gray-300 shadow-sm text-sm focus:ring-blue-500"
            placeholder="UUID del cohorte"
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
