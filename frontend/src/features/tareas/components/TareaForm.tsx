/**
 * TareaForm — RHF + Zod form for creating a new Tarea.
 * Task 3.7. < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { tareaCreateSchema, type TareaCreateFormValues } from '../services/tareaSchema'
import { useCrearTarea } from '../hooks/tareasHooks'

interface Props {
  onClose: () => void
}

export default function TareaForm({ onClose }: Props) {
  const crearMutation = useCrearTarea()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TareaCreateFormValues>({
    resolver: zodResolver(tareaCreateSchema),
    defaultValues: {
      asignado_a: '',
      descripcion: '',
      materia_id: null,
      contexto_id: null,
      contexto_tipo: null,
    },
  })

  function onSubmit(data: TareaCreateFormValues) {
    crearMutation.mutate(
      {
        asignado_a: data.asignado_a,
        descripcion: data.descripcion,
        materia_id: data.materia_id ?? null,
        contexto_id: data.contexto_id ?? null,
        contexto_tipo: data.contexto_tipo ?? null,
      },
      {
        onSuccess: () => {
          toast.success('Tarea creada correctamente')
          onClose()
        },
        onError: (err) => {
          toast.error((err as { detail?: string }).detail ?? 'Error al crear la tarea')
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="asignado_a" className="block text-sm font-medium text-gray-700">
          Docente asignado (ID) <span className="text-red-500">*</span>
        </label>
        <input
          id="asignado_a"
          type="text"
          {...register('asignado_a')}
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
        {errors.asignado_a && (
          <p className="mt-1 text-xs text-red-600">{errors.asignado_a.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="descripcion" className="block text-sm font-medium text-gray-700">
          Descripción <span className="text-red-500">*</span>
        </label>
        <textarea
          id="descripcion"
          rows={3}
          {...register('descripcion')}
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
        {errors.descripcion && (
          <p className="mt-1 text-xs text-red-600">{errors.descripcion.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="materia_id" className="block text-sm font-medium text-gray-700">
          Materia (ID, opcional)
        </label>
        <input
          id="materia_id"
          type="text"
          {...register('materia_id')}
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      {errors.root && (
        <p className="text-xs text-red-600">{errors.root.message}</p>
      )}

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isSubmitting || crearMutation.isPending}
          className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {crearMutation.isPending ? 'Creando…' : 'Crear tarea'}
        </button>
      </div>
    </form>
  )
}
