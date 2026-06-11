/**
 * NuevoHiloForm — form to start a new 1:1 messaging thread.
 * Uses UsuarioCombobox (searchable) for destinatario_id instead of raw UUID input.
 * The combobox is fed by useBuscarUsuariosInbox (GET /inbox/usuarios?q=).
 * < 200 LOC. No `any`. PascalCase. Tailwind only.
 */
import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui/Button'
import { nuevoHiloSchema } from '../services/mensajeriaService'
import { useIniciarHilo, useBuscarUsuariosInbox } from '../hooks/mensajeriaHooks'
import UsuarioCombobox from '@/features/asignaciones/components/UsuarioCombobox'

// The schema still validates that destinatario_id is a non-empty string.
// UUID format validation is enforced at the service layer on the backend.
const formSchema = nuevoHiloSchema.extend({
  destinatario_id: z
    .string({ required_error: 'Seleccioná un destinatario' })
    .min(1, 'Seleccioná un destinatario'),
})

type NuevoHiloFormValues = z.infer<typeof formSchema>

interface NuevoHiloFormProps {
  onSuccess: () => void
  onCancel: () => void
}

export function NuevoHiloForm({ onSuccess, onCancel }: NuevoHiloFormProps) {
  const [domainError, setDomainError] = useState<string | null>(null)
  const iniciarHilo = useIniciarHilo()

  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<NuevoHiloFormValues>({ resolver: zodResolver(formSchema) })

  const onSubmit = async (values: NuevoHiloFormValues) => {
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
          Destinatario <span className="text-warn">*</span>
        </label>
        <Controller
          name="destinatario_id"
          control={control}
          render={({ field }) => (
            <UsuarioCombobox
              value={field.value ?? null}
              onChange={(id) => field.onChange(id ?? '')}
              error={errors.destinatario_id?.message}
              searchHook={useBuscarUsuariosInbox}
            />
          )}
        />
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
