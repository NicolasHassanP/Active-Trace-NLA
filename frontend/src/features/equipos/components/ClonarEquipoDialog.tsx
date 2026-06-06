/**
 * ClonarEquipoDialog — dialog for POST /equipos/clonar.
 * Task 1.9. < 200 LOC.
 */
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useClonarEquipo } from '../hooks/equiposHooks'
import { Button } from '@/shared/components/ui'

const schema = z.object({
  origen_materia_id: z.string().min(1, 'Obligatorio'),
  origen_carrera_id: z.string().min(1, 'Obligatorio'),
  origen_cohorte_id: z.string().min(1, 'Obligatorio'),
  destino_materia_id: z.string().min(1, 'Obligatorio'),
  destino_carrera_id: z.string().min(1, 'Obligatorio'),
  destino_cohorte_id: z.string().min(1, 'Obligatorio'),
  desde: z.string().min(1, 'Obligatorio'),
  hasta: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

export default function ClonarEquipoDialog() {
  const [open, setOpen] = useState(false)
  const mutation = useClonarEquipo()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  function onSubmit(values: FormValues) {
    mutation.mutate(
      { ...values, hasta: values.hasta || null },
      {
        onSuccess: (data) => {
          toast.success(`Clonadas: ${data.clonadas}, omitidas: ${data.omitidas}`)
          reset()
          setOpen(false)
        },
        onError: (err) => {
          toast.error((err as { detail?: string }).detail ?? 'Error al clonar')
        },
      },
    )
  }

  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Clonar equipo
      </Button>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Clonar equipo</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            {(['origen_materia_id', 'origen_carrera_id', 'origen_cohorte_id'] as const).map((f) => (
              <div key={f}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{f.replace('origen_', '')}</label>
                <input {...register(f)} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
                {errors[f] && <p className="mt-1 text-xs text-red-600">{errors[f]?.message}</p>}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3">
            {(['destino_materia_id', 'destino_carrera_id', 'destino_cohorte_id'] as const).map((f) => (
              <div key={f}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{f.replace('destino_', '')} destino</label>
                <input {...register(f)} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
                {errors[f] && <p className="mt-1 text-xs text-red-600">{errors[f]?.message}</p>}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Desde</label>
              <input type="date" {...register('desde')} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
              {errors.desde && <p className="mt-1 text-xs text-red-600">{errors.desde.message}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Hasta (opcional)</label>
              <input type="date" {...register('hasta')} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" isLoading={mutation.isPending} disabled={mutation.isPending}>
              Clonar
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
