/**
 * AsignacionForm — React Hook Form + Zod form for POST and PATCH /api/v1/asignaciones.
 *
 * Handles both create (no initialValues) and edit (initialValues populated from row).
 * In CREATE mode, usuario_id is selected via UsuarioCombobox (searchable dropdown).
 * In EDIT mode, usuario_id is not editable (displayed as-is).
 * tenant_id/identity never in the body — resolved from the JWT on the backend.
 * Submit logic lives in the parent page (onSubmit prop). < 200 LOC.
 */
import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import type { AsignacionCreate, AsignacionUpdate, RolAsignacion } from '../types'
import { ROLES_ASIGNACION } from '../types'
import UsuarioCombobox from './UsuarioCombobox'

const ROLES = ROLES_ASIGNACION as [RolAsignacion, ...RolAsignacion[]]

const schema = z.object({
  usuario_id: z.string().uuid('UUID inválido'),
  rol: z.enum(ROLES),
  desde: z.string().min(1, 'Obligatorio'),
  hasta: z.string().nullable(),
  materia_id: z.string().nullable(),
  carrera_id: z.string().nullable(),
  cohorte_id: z.string().nullable(),
  responsable_id: z.string().nullable(),
})

type FormValues = z.infer<typeof schema>

/** Shared shape for create and edit. */
export interface AsignacionFormValues {
  usuario_id: string
  rol: RolAsignacion
  desde: string
  hasta: string | null
  materia_id: string | null
  carrera_id: string | null
  cohorte_id: string | null
  responsable_id: string | null
}

interface Props {
  /** Populated when editing an existing asignacion; undefined = create mode. */
  initialValues?: AsignacionFormValues
  onSubmit: (values: AsignacionCreate | AsignacionUpdate) => void
  onCancel: () => void
  isSubmitting: boolean
}

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'
const labelClass = 'mb-1 block text-sm font-medium text-gray-700'

const EMPTY_DEFAULTS: FormValues = {
  usuario_id: '',
  rol: 'PROFESOR',
  desde: '',
  hasta: null,
  materia_id: null,
  carrera_id: null,
  cohorte_id: null,
  responsable_id: null,
}

function toFormDefaults(v: AsignacionFormValues | undefined): FormValues {
  if (!v) return EMPTY_DEFAULTS
  return {
    usuario_id: v.usuario_id,
    rol: v.rol,
    desde: v.desde,
    hasta: v.hasta ?? null,
    materia_id: v.materia_id ?? null,
    carrera_id: v.carrera_id ?? null,
    cohorte_id: v.cohorte_id ?? null,
    responsable_id: v.responsable_id ?? null,
  }
}

export default function AsignacionForm({
  initialValues,
  onSubmit,
  onCancel,
  isSubmitting,
}: Props) {
  const isEdit = initialValues !== undefined

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: toFormDefaults(initialValues),
  })

  // When initialValues change (switching between rows), reset to new values
  useEffect(() => {
    reset(toFormDefaults(initialValues))
  }, [initialValues, reset])

  function submit(values: FormValues) {
    if (isEdit) {
      // PATCH — only send changed fields (all optional)
      const update: AsignacionUpdate = {
        rol: values.rol,
        desde: values.desde,
        hasta: values.hasta,
        materia_id: values.materia_id,
        carrera_id: values.carrera_id,
        cohorte_id: values.cohorte_id,
        responsable_id: values.responsable_id,
      }
      onSubmit(update)
    } else {
      // POST — required fields + optionals
      const create: AsignacionCreate = {
        usuario_id: values.usuario_id,
        rol: values.rol,
        desde: values.desde,
        hasta: values.hasta,
        materia_id: values.materia_id,
        carrera_id: values.carrera_id,
        cohorte_id: values.cohorte_id,
        responsable_id: values.responsable_id,
      }
      onSubmit(create)
    }
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="max-w-2xl space-y-4"
      data-testid="asignacion-form"
    >
      {!isEdit && (
        <div>
          <label className={labelClass} htmlFor="asgn-usuario-id">
            Usuario
          </label>
          <Controller
            name="usuario_id"
            control={control}
            render={({ field }) => (
              <UsuarioCombobox
                value={field.value || null}
                onChange={(id) => field.onChange(id ?? '')}
                error={errors.usuario_id?.message}
              />
            )}
          />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label className={labelClass} htmlFor="asgn-rol">
            Rol
          </label>
          <select id="asgn-rol" {...register('rol')} data-testid="asgn-rol" className={inputClass}>
            {ROLES_ASIGNACION.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelClass} htmlFor="asgn-desde">
            Desde
          </label>
          <input
            id="asgn-desde"
            type="date"
            {...register('desde')}
            data-testid="asgn-desde"
            className={inputClass}
          />
          {errors.desde && <p className="mt-1 text-xs text-red-600">{errors.desde.message}</p>}
        </div>

        <div>
          <label className={labelClass} htmlFor="asgn-hasta">
            Hasta (opcional)
          </label>
          <input
            id="asgn-hasta"
            type="date"
            {...register('hasta')}
            data-testid="asgn-hasta"
            className={inputClass}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label className={labelClass} htmlFor="asgn-materia-id">
            Materia ID (opcional)
          </label>
          <input
            id="asgn-materia-id"
            {...register('materia_id')}
            data-testid="asgn-materia-id"
            placeholder="UUID"
            className={inputClass}
          />
        </div>

        <div>
          <label className={labelClass} htmlFor="asgn-carrera-id">
            Carrera ID (opcional)
          </label>
          <input
            id="asgn-carrera-id"
            {...register('carrera_id')}
            data-testid="asgn-carrera-id"
            placeholder="UUID"
            className={inputClass}
          />
        </div>

        <div>
          <label className={labelClass} htmlFor="asgn-cohorte-id">
            Cohorte ID (opcional)
          </label>
          <input
            id="asgn-cohorte-id"
            {...register('cohorte_id')}
            data-testid="asgn-cohorte-id"
            placeholder="UUID"
            className={inputClass}
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" data-testid="asgn-submit" isLoading={isSubmitting} disabled={isSubmitting}>
          {isEdit ? 'Guardar cambios' : 'Crear asignación'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
