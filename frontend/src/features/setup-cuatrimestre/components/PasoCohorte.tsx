/**
 * PasoCohorte — Step 1: Select/create cohorte.
 * Task 7.4. Reuses academic structure via simple input fields.
 * The cohorte_id is used by downstream steps.
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  cohorte_id: z.string().min(1, 'Cohorte ID obligatorio'),
  nombre: z.string().min(1, 'Nombre de cohorte obligatorio'),
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
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  function onSubmit(data: FormValues) {
    // In a real implementation this would call POST /api/v1/cohortes or select existing.
    // For C-23 scope: wizard only needs the cohorte_id to pass to subsequent steps.
    // The ADMIN module manages full cohorte CRUD (D6 — not in C-23 scope).
    onSuccess(data.cohorte_id)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-cohorte">
      <p className="text-sm text-gray-600">
        Indicá el identificador de la cohorte para este cuatrimestre. Si ya existe, lo reutilizamos;
        si es nueva, coordiná su creación con el Administrador.
      </p>

      <div>
        <label className="block text-sm font-medium text-gray-700">ID de cohorte</label>
        <input
          {...register('cohorte_id')}
          placeholder="ej. coh-2026-1"
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        {errors.cohorte_id && (
          <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Nombre / período</label>
        <input
          {...register('nombre')}
          placeholder="ej. 2026-1"
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        {errors.nombre && (
          <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Guardando…' : 'Confirmar cohorte'}
      </button>
    </form>
  )
}
