/**
 * UsuarioForm — RHF + Zod form for POST/PATCH /api/v1/admin/usuarios.
 * Create mode: email + nombre + apellidos + legajo (optional) + estado.
 * Edit mode: same fields, pre-populated.
 *
 * CONTRATO OQ-3 (enforced explicitly):
 *   NEVER renders: dni, cuil, cbu, alias_cbu, banco, facturador,
 *   legajo_profesional, regional, auth_identity_id.
 *   Those are PII financiera → C-24 only.
 *
 * tenant_id never in the body (JWT interceptor handles it, rule #8/#9).
 * errorMessage prop displays 409 ConflictoEmail / 404 errors from parseDomainError.
 * < 200 LOC.
 */
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import type { UsuarioCreate, UsuarioUpdate, UsuarioRead, UsuarioEstado } from '../types'
import { ESTADOS_USUARIO } from '../types'

// ---------------------------------------------------------------------------
// Zod schema — non-PII fields only
// ---------------------------------------------------------------------------

const schema = z.object({
  email: z.string().min(1, 'Obligatorio').email('Email inválido'),
  nombre: z.string().min(1, 'Obligatorio'),
  apellidos: z.string().min(1, 'Obligatorio'),
  legajo: z.string().optional(),
  estado: z.enum(['activo', 'inactivo'] as [UsuarioEstado, UsuarioEstado]),
})

type FormValues = z.infer<typeof schema>

interface Props {
  initialValues?: UsuarioRead
  onSubmit: (values: UsuarioCreate | UsuarioUpdate) => void
  onCancel: () => void
  isSubmitting: boolean
  errorMessage?: string
}

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'
const labelClass = 'mb-1 block text-sm font-medium text-gray-700'

export default function UsuarioForm({ initialValues, onSubmit, onCancel, isSubmitting, errorMessage }: Props) {
  const isEdit = initialValues !== undefined

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: initialValues?.email ?? '',
      nombre: initialValues?.nombre ?? '',
      apellidos: initialValues?.apellidos ?? '',
      legajo: initialValues?.legajo ?? '',
      estado: initialValues?.estado ?? 'activo',
    },
  })

  useEffect(() => {
    reset({
      email: initialValues?.email ?? '',
      nombre: initialValues?.nombre ?? '',
      apellidos: initialValues?.apellidos ?? '',
      legajo: initialValues?.legajo ?? '',
      estado: initialValues?.estado ?? 'activo',
    })
  }, [initialValues, reset])

  function submit(values: FormValues) {
    // Build non-PII body — NEVER include dni/cuil/cbu/alias_cbu/tenant_id
    const payload: UsuarioCreate | UsuarioUpdate = {
      email: values.email,
      nombre: values.nombre,
      apellidos: values.apellidos,
      legajo: values.legajo || null,
      estado: values.estado,
    }
    onSubmit(payload)
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="max-w-lg space-y-4"
      data-testid="usuario-form"
    >
      {errorMessage && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {/* email */}
      <div>
        <label className={labelClass} htmlFor="usuario-email">Email</label>
        <input
          id="usuario-email"
          data-testid="usuario-email"
          type="email"
          {...register('email')}
          className={inputClass}
        />
        {errors.email && (
          <p data-testid="usuario-email-error" className="mt-1 text-xs text-red-600">
            {errors.email.message}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* nombre */}
        <div>
          <label className={labelClass} htmlFor="usuario-nombre">Nombre</label>
          <input
            id="usuario-nombre"
            data-testid="usuario-nombre"
            {...register('nombre')}
            className={inputClass}
          />
          {errors.nombre && (
            <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>
          )}
        </div>

        {/* apellidos */}
        <div>
          <label className={labelClass} htmlFor="usuario-apellidos">Apellidos</label>
          <input
            id="usuario-apellidos"
            data-testid="usuario-apellidos"
            {...register('apellidos')}
            className={inputClass}
          />
          {errors.apellidos && (
            <p className="mt-1 text-xs text-red-600">{errors.apellidos.message}</p>
          )}
        </div>
      </div>

      {/* legajo — optional */}
      <div>
        <label className={labelClass} htmlFor="usuario-legajo">Legajo (opcional)</label>
        <input
          id="usuario-legajo"
          data-testid="usuario-legajo"
          {...register('legajo')}
          className={inputClass}
        />
      </div>

      {/* estado */}
      <div>
        <label className={labelClass} htmlFor="usuario-estado">Estado</label>
        <select
          id="usuario-estado"
          data-testid="usuario-estado"
          {...register('estado')}
          className={inputClass}
        >
          {ESTADOS_USUARIO.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-3">
        <Button
          type="submit"
          data-testid="usuario-submit"
          isLoading={isSubmitting}
          disabled={isSubmitting}
        >
          {isEdit ? 'Guardar cambios' : 'Crear usuario'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
