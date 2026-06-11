/**
 * PasoCohorte — Step 1: Select the cohorte for the new cuatrimestre.
 * Task 7.4. The cohorte_id is used by downstream steps.
 *
 * UX: cohorte is a <select> by nombre (from GET /admin/cohortes). New cohortes
 * are created by the Administrator in the estructura module; once created they
 * appear in this list. The período (nombre) is derived from the selection.
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/shared/components/ui'
import { listarTodosCohortes } from '@/features/monitores/services/monitoresService'

const schema = z.object({
  cohorte_id: z.string().min(1, 'Seleccioná una cohorte'),
  nombre: z.string().min(1),
})

type FormValues = z.infer<typeof schema>

interface PasoCohorteProps {
  onSuccess: (cohorteId: string) => void
  onError: (msg: string) => void
}

export default function PasoCohorte({ onSuccess, onError: _onError }: PasoCohorteProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const cohortesQuery = useQuery({ queryKey: ['admin-cohortes'], queryFn: listarTodosCohortes })
  const cohortes = cohortesQuery.data ?? []

  const selectedNombre = watch('nombre')

  function handleSelect(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value
    const cohorte = cohortes.find((c) => c.id === id)
    setValue('nombre', cohorte?.nombre ?? '', { shouldValidate: true })
  }

  function onSubmit(data: FormValues) {
    // Wizard only needs the cohorte_id to pass to subsequent steps.
    // Full cohorte CRUD lives in the ADMIN estructura module (D6 — not in scope here).
    onSuccess(data.cohorte_id)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-cohorte">
      <p className="text-sm text-gray-600">
        Seleccioná la cohorte de este cuatrimestre. Si es nueva, primero coordiná su creación con el
        Administrador y luego aparecerá en esta lista.
      </p>

      <div>
        <label className="block text-sm font-medium text-gray-700">Cohorte</label>
        <select
          {...register('cohorte_id', { onChange: handleSelect })}
          data-testid="cohorte-id"
          disabled={cohortesQuery.isLoading}
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">
            {cohortesQuery.isLoading ? 'Cargando…' : '-- Seleccioná una cohorte --'}
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

      {/* nombre is derived from the selected cohorte (kept in form state, shown read-only) */}
      <input type="hidden" {...register('nombre')} />
      {selectedNombre && (
        <p className="text-sm text-gray-600">
          Período: <span className="font-medium text-gray-800">{selectedNombre}</span>
        </p>
      )}

      <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
        {isSubmitting ? 'Guardando…' : 'Confirmar cohorte'}
      </Button>
    </form>
  )
}
