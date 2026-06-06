/**
 * PasoAvisoBienvenida — Step 7: Publish welcome aviso.
 * Task 7.10. Reuses avisosService.crearAviso.
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { crearAviso } from '@/features/avisos/services/avisosService'
import { parseDomainError } from '@/shared/services/domainError'
import type { AvisoSeveridad } from '@/features/avisos/types'
import { Button } from '@/shared/components/ui'

const schema = z.object({
  titulo: z.string().min(1, 'Título obligatorio'),
  cuerpo: z.string().min(1, 'Cuerpo obligatorio'),
  inicio_en: z.string().min(1, 'Fecha de inicio obligatoria'),
  fin_en: z.string().min(1, 'Fecha de fin obligatoria'),
  severidad: z.enum(['Info', 'Advertencia', 'Critico']).default('Info'),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoAvisoBienvenida({ onSuccess, onError }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      titulo: 'Inicio de cuatrimestre',
      cuerpo: 'Bienvenidos al nuevo cuatrimestre. Les informamos el inicio de actividades.',
      severidad: 'Info',
    },
  })

  async function onSubmit(data: FormValues) {
    try {
      await crearAviso({
        alcance: 'Global',
        severidad: data.severidad as AvisoSeveridad,
        titulo: data.titulo,
        cuerpo: data.cuerpo,
        inicio_en: data.inicio_en,
        fin_en: data.fin_en,
        requiere_ack: false,
        activo: true,
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
      data-testid="paso-aviso-bienvenida"
    >
      <p className="text-sm text-gray-600">
        Publicá un aviso de bienvenida para todos los docentes de la institución.
      </p>

      <div>
        <label className="block text-sm font-medium text-gray-700">Título del aviso</label>
        <input {...register('titulo')} className={inputClass} />
        {errors.titulo && (
          <p className="mt-1 text-xs text-red-600">{errors.titulo.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Cuerpo del aviso</label>
        <textarea
          {...register('cuerpo')}
          rows={3}
          className={inputClass}
        />
        {errors.cuerpo && (
          <p className="mt-1 text-xs text-red-600">{errors.cuerpo.message}</p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Severidad</label>
          <select {...register('severidad')} className={inputClass}>
            {(['Info', 'Advertencia', 'Critico'] as const).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Inicio</label>
          <input {...register('inicio_en')} type="datetime-local" className={inputClass} />
          {errors.inicio_en && (
            <p className="mt-1 text-xs text-red-600">{errors.inicio_en.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Fin</label>
          <input {...register('fin_en')} type="datetime-local" className={inputClass} />
          {errors.fin_en && (
            <p className="mt-1 text-xs text-red-600">{errors.fin_en.message}</p>
          )}
        </div>
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
        {isSubmitting ? 'Publicando…' : 'Publicar aviso de bienvenida'}
      </Button>
    </form>
  )
}
