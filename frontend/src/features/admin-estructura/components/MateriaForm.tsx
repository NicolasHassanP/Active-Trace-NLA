/**
 * MateriaForm — RHF + Zod form for POST/PATCH /api/v1/admin/materias.
 * Create mode: codigo + nombre. Edit mode: + estado.
 * tenant_id never in the body.
 * errorMessage prop displays 409/404 domain errors from parseDomainError.
 * < 200 LOC.
 */
import { useEffect } from 'react'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import type { MateriaCreate, MateriaUpdate, MateriaRead, EstadoEstructura } from '../types'
import { ESTADOS_ESTRUCTURA } from '../types'

const createSchema = z.object({
  codigo: z.string().min(1, 'Obligatorio'),
  nombre: z.string().min(1, 'Obligatorio'),
})

const editSchema = createSchema.extend({
  estado: z.enum(['activa', 'inactiva'] as [EstadoEstructura, EstadoEstructura]),
})

type EditValues = z.infer<typeof editSchema>

interface Props {
  initialValues?: MateriaRead
  onSubmit: (values: MateriaCreate | MateriaUpdate) => void
  onCancel: () => void
  isSubmitting: boolean
  errorMessage?: string
}

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'
const labelClass = 'mb-1 block text-sm font-medium text-gray-700'

export default function MateriaForm({ initialValues, onSubmit, onCancel, isSubmitting, errorMessage }: Props) {
  const isEdit = initialValues !== undefined

  const { register, handleSubmit, reset, formState: { errors } } = useForm<EditValues>({
    resolver: zodResolver(isEdit ? editSchema : createSchema) as unknown as Resolver<EditValues>,
    defaultValues: {
      codigo: initialValues?.codigo ?? '',
      nombre: initialValues?.nombre ?? '',
      estado: initialValues?.estado ?? 'activa',
    },
  })

  useEffect(() => {
    reset({
      codigo: initialValues?.codigo ?? '',
      nombre: initialValues?.nombre ?? '',
      estado: initialValues?.estado ?? 'activa',
    })
  }, [initialValues, reset])

  function submit(values: EditValues) {
    if (isEdit) {
      const update: MateriaUpdate = { codigo: values.codigo, nombre: values.nombre, estado: values.estado }
      onSubmit(update)
    } else {
      const create: MateriaCreate = { codigo: values.codigo, nombre: values.nombre }
      onSubmit(create)
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="max-w-lg space-y-4" data-testid="materia-form">
      {errorMessage && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{errorMessage}</div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass} htmlFor="materia-codigo">Código</label>
          <input id="materia-codigo" data-testid="materia-codigo" {...register('codigo')} className={inputClass} />
          {errors.codigo && <p className="mt-1 text-xs text-red-600">{errors.codigo.message}</p>}
        </div>
        <div>
          <label className={labelClass} htmlFor="materia-nombre">Nombre</label>
          <input id="materia-nombre" data-testid="materia-nombre" {...register('nombre')} className={inputClass} />
          {errors.nombre && <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>}
        </div>
      </div>

      {isEdit && (
        <div>
          <label className={labelClass} htmlFor="materia-estado">Estado</label>
          <select id="materia-estado" data-testid="materia-estado" {...register('estado')} className={inputClass}>
            {ESTADOS_ESTRUCTURA.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>
      )}

      <div className="flex gap-3">
        <Button type="submit" data-testid="materia-submit" isLoading={isSubmitting} disabled={isSubmitting}>
          {isEdit ? 'Guardar cambios' : 'Crear materia'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
      </div>
    </form>
  )
}
