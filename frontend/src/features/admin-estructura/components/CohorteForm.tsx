/**
 * CohorteForm — RHF + Zod form for POST/PATCH /api/v1/admin/cohortes.
 * carrera_id REQUIRED. vig_hasta nullable = cohorte abierta (reusar lógica de PasoCohorte).
 * tenant_id never in the body. < 200 LOC.
 */
import { useEffect } from 'react'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import type { CohorteCreate, CohorteUpdate, CohorteRead, EstadoEstructura, CarreraRead } from '../types'
import { ESTADOS_ESTRUCTURA } from '../types'

const createSchema = z.object({
  carrera_id: z.string().min(1, 'Obligatorio'),
  nombre: z.string().min(1, 'Obligatorio'),
  anio: z.coerce.number().int().min(2000, 'Año inválido'),
  vig_desde: z.string().min(1, 'Obligatorio'),
  vig_hasta: z.string().nullable().optional(),
})

const editSchema = createSchema.extend({
  estado: z.enum(['activa', 'inactiva'] as [EstadoEstructura, EstadoEstructura]),
})

type EditValues = z.infer<typeof editSchema>

interface Props {
  carreras: CarreraRead[]
  initialValues?: CohorteRead
  onSubmit: (values: CohorteCreate | CohorteUpdate) => void
  onCancel: () => void
  isSubmitting: boolean
  errorMessage?: string
}

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'
const labelClass = 'mb-1 block text-sm font-medium text-gray-700'

export default function CohorteForm({ carreras, initialValues, onSubmit, onCancel, isSubmitting, errorMessage }: Props) {
  const isEdit = initialValues !== undefined

  const { register, handleSubmit, reset, formState: { errors } } = useForm<EditValues>({
    resolver: zodResolver(isEdit ? editSchema : createSchema) as unknown as Resolver<EditValues>,
    defaultValues: {
      carrera_id: initialValues?.carrera_id ?? '',
      nombre: initialValues?.nombre ?? '',
      anio: initialValues?.anio ?? new Date().getFullYear(),
      vig_desde: initialValues?.vig_desde ?? '',
      vig_hasta: initialValues?.vig_hasta ?? '',
      estado: initialValues?.estado ?? 'activa',
    },
  })

  useEffect(() => {
    reset({
      carrera_id: initialValues?.carrera_id ?? '',
      nombre: initialValues?.nombre ?? '',
      anio: initialValues?.anio ?? new Date().getFullYear(),
      vig_desde: initialValues?.vig_desde ?? '',
      vig_hasta: initialValues?.vig_hasta ?? '',
      estado: initialValues?.estado ?? 'activa',
    })
  }, [initialValues, reset])

  function submit(values: EditValues) {
    // Normalize vig_hasta: empty string → null (cohorte abierta)
    const vigHasta = values.vig_hasta && values.vig_hasta.trim() !== '' ? values.vig_hasta : null

    if (isEdit) {
      const update: CohorteUpdate = {
        nombre: values.nombre,
        anio: values.anio,
        vig_desde: values.vig_desde,
        vig_hasta: vigHasta,
        estado: values.estado,
      }
      onSubmit(update)
    } else {
      const create: CohorteCreate = {
        carrera_id: values.carrera_id,
        nombre: values.nombre,
        anio: values.anio,
        vig_desde: values.vig_desde,
        vig_hasta: vigHasta,
      }
      onSubmit(create)
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="max-w-lg space-y-4" data-testid="cohorte-form">
      {errorMessage && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorMessage}</div>
      )}

      <div>
        <label className={labelClass} htmlFor="cohorte-carrera-id">Carrera</label>
        <select id="cohorte-carrera-id" data-testid="cohorte-carrera-id" {...register('carrera_id')} className={inputClass}>
          <option value="">-- Seleccionar carrera --</option>
          {carreras.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
        </select>
        {errors.carrera_id && (
          <p data-testid="cohorte-carrera-error" className="mt-1 text-xs text-red-600">{errors.carrera_id.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass} htmlFor="cohorte-nombre">Nombre</label>
          <input id="cohorte-nombre" data-testid="cohorte-nombre" {...register('nombre')} className={inputClass} />
          {errors.nombre && <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>}
        </div>
        <div>
          <label className={labelClass} htmlFor="cohorte-anio">Año</label>
          <input id="cohorte-anio" type="number" data-testid="cohorte-anio" {...register('anio')} className={inputClass} />
          {errors.anio && <p className="mt-1 text-xs text-red-600">{errors.anio.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass} htmlFor="cohorte-vig-desde">Vigencia desde</label>
          <input id="cohorte-vig-desde" type="date" data-testid="cohorte-vig-desde" {...register('vig_desde')} className={inputClass} />
          {errors.vig_desde && <p className="mt-1 text-xs text-red-600">{errors.vig_desde.message}</p>}
        </div>
        <div>
          <label className={labelClass} htmlFor="cohorte-vig-hasta">Vigencia hasta (opcional)</label>
          <input id="cohorte-vig-hasta" type="date" data-testid="cohorte-vig-hasta" {...register('vig_hasta')} className={inputClass} />
          <p className="mt-0.5 text-xs text-gray-400">Dejá vacío para cohorte abierta</p>
        </div>
      </div>

      {isEdit && (
        <div>
          <label className={labelClass} htmlFor="cohorte-estado">Estado</label>
          <select id="cohorte-estado" data-testid="cohorte-estado" {...register('estado')} className={inputClass}>
            {ESTADOS_ESTRUCTURA.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>
      )}

      <div className="flex gap-3">
        <Button type="submit" data-testid="cohorte-submit" isLoading={isSubmitting} disabled={isSubmitting}>
          {isEdit ? 'Guardar cambios' : 'Crear cohorte'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
      </div>
    </form>
  )
}
