/**
 * EditarInstanciaDialog — modal form for editing mutable fields of an instancia.
 * Fields: estado, meet_url, video_url, comentario (mirrors EditarInstanciaRequest).
 * Uses RHF + Zod. < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import { useEditarInstancia } from '../hooks/encuentrosCoordHooks'
import type { InstanciaEncuentroRead, InstanciaEncuentroEstado } from '../types'
import { toast } from 'sonner'

const ESTADOS: InstanciaEncuentroEstado[] = ['Programado', 'Realizado', 'Cancelado']

const schema = z.object({
  estado: z.enum(['Programado', 'Realizado', 'Cancelado']).nullable().optional(),
  meet_url: z.string().url('URL inválida').nullable().optional().or(z.literal('')),
  video_url: z.string().url('URL inválida').nullable().optional().or(z.literal('')),
  comentario: z.string().nullable().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  instancia: InstanciaEncuentroRead
  onClose: () => void
}

export default function EditarInstanciaDialog({ instancia, onClose }: Props) {
  const editarMutation = useEditarInstancia()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      estado: instancia.estado,
      meet_url: instancia.meet_url ?? '',
      video_url: instancia.video_url ?? '',
      comentario: instancia.comentario ?? '',
    },
  })

  async function onSubmit(data: FormValues) {
    await editarMutation.mutateAsync({
      id: instancia.id,
      payload: {
        estado: data.estado ?? undefined,
        meet_url: data.meet_url || null,
        video_url: data.video_url || null,
        comentario: data.comentario || null,
      },
    })
    toast.success('Instancia actualizada')
    onClose()
  }

  return (
    /* Backdrop */
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Editar instancia de encuentro"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-800">
          Editar instancia — {instancia.titulo}
        </h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Estado</label>
            <select
              {...register('estado')}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              {ESTADOS.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
            {errors.estado && (
              <p className="mt-1 text-xs text-red-600">{errors.estado.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">URL Google Meet</label>
            <input
              type="url"
              {...register('meet_url')}
              placeholder="https://meet.google.com/..."
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            {errors.meet_url && (
              <p className="mt-1 text-xs text-red-600">{errors.meet_url.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">URL Grabación</label>
            <input
              type="url"
              {...register('video_url')}
              placeholder="https://..."
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            {errors.video_url && (
              <p className="mt-1 text-xs text-red-600">{errors.video_url.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Comentario</label>
            <textarea
              {...register('comentario')}
              rows={3}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={isSubmitting}
              isLoading={isSubmitting}
            >
              {isSubmitting ? 'Guardando…' : 'Guardar cambios'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
