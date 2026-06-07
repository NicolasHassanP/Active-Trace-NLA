import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { nuevoHiloSchema, type NuevoHiloValues } from '../services/mensajeriaService'
import { useIniciarHilo } from '../hooks/mensajeriaHooks'

interface NuevoHiloFormProps {
  onSuccess: () => void
  onCancel: () => void
}

export function NuevoHiloForm({ onSuccess, onCancel }: NuevoHiloFormProps) {
  const [domainError, setDomainError] = useState<string | null>(null)
  const iniciarHilo = useIniciarHilo()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<NuevoHiloValues>({ resolver: zodResolver(nuevoHiloSchema) })

  const onSubmit = async (values: NuevoHiloValues) => {
    setDomainError(null)
    try {
      await iniciarHilo.mutateAsync({
        destinatario_id: values.destinatario_id,
        asunto: values.asunto,
        cuerpo: values.cuerpo,
      })
      reset()
      onSuccess()
    } catch (err: unknown) {
      const error = err as { status?: number; message?: string }
      if (error?.status === 404) {
        setDomainError('El destinatario no existe en este tenant.')
      } else if (error?.status === 409) {
        setDomainError('Ya existe un hilo de mensajería con este destinatario.')
      } else {
        setDomainError('Error al crear el hilo. Intentá de nuevo.')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-4">
      <h3 className="text-[14px] font-bold text-ink">Nuevo mensaje</h3>

      <div className="flex flex-col gap-1">
        <label className="text-[12px] font-bold text-mut uppercase tracking-wide">
          ID de destinatario <span className="text-warn">*</span>
        </label>
        <input
          {...register('destinatario_id')}
          placeholder="UUID del destinatario"
          className="w-full rounded-[9px] border border-line px-3 py-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-ind"
        />
        {errors.destinatario_id && (
          <p className="text-[11.5px] text-warn">{errors.destinatario_id.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[12px] font-bold text-mut uppercase tracking-wide">Asunto</label>
        <input
          {...register('asunto')}
          placeholder="Asunto (opcional)"
          className="w-full rounded-[9px] border border-line px-3 py-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-ind"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[12px] font-bold text-mut uppercase tracking-wide">
          Mensaje <span className="text-warn">*</span>
        </label>
        <textarea
          {...register('cuerpo')}
          rows={4}
          placeholder="Escribí tu mensaje..."
          className="w-full rounded-[9px] border border-line px-3 py-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-ind resize-none"
        />
        {errors.cuerpo && (
          <p className="text-[11.5px] text-warn">{errors.cuerpo.message}</p>
        )}
      </div>

      {domainError && (
        <p className="text-[12px] text-warn bg-warnBg rounded-[8px] px-3 py-2">{domainError}</p>
      )}

      <div className="flex gap-2 justify-end">
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" size="sm" isLoading={iniciarHilo.isPending}>
          Enviar
        </Button>
      </div>
    </form>
  )
}
