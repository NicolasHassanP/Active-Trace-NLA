import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { responderSchema, type ResponderValues } from '../services/mensajeriaService'
import { useResponder } from '../hooks/mensajeriaHooks'

interface ResponderFormProps {
  hiloId: string
  onSuccess: () => void
}

export function ResponderForm({ hiloId, onSuccess }: ResponderFormProps) {
  const responder = useResponder(hiloId)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ResponderValues>({ resolver: zodResolver(responderSchema) })

  const onSubmit = async (values: ResponderValues) => {
    await responder.mutateAsync({ asunto: values.asunto, cuerpo: values.cuerpo })
    reset()
    onSuccess()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3 p-4 border-t border-line bg-white">
      <div className="flex flex-col gap-1">
        <label className="text-[12px] font-bold text-mut uppercase tracking-wide">
          Asunto <span className="text-warn">*</span>
        </label>
        <input
          {...register('asunto')}
          placeholder="Asunto de la respuesta"
          className="w-full rounded-[9px] border border-line px-3 py-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-ind"
        />
        {errors.asunto && (
          <p className="text-[11.5px] text-warn">{errors.asunto.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[12px] font-bold text-mut uppercase tracking-wide">
          Respuesta <span className="text-warn">*</span>
        </label>
        <textarea
          {...register('cuerpo')}
          rows={3}
          placeholder="Escribí tu respuesta..."
          className="w-full rounded-[9px] border border-line px-3 py-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-ind resize-none"
        />
        {errors.cuerpo && (
          <p className="text-[11.5px] text-warn">{errors.cuerpo.message}</p>
        )}
      </div>

      <div className="flex justify-end">
        <Button type="submit" size="sm" isLoading={responder.isPending}>
          Responder
        </Button>
      </div>
    </form>
  )
}
