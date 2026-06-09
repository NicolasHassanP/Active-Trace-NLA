/**
 * PerfilForm — React Hook Form + Zod form for editing the own profile.
 * Editable fields → inputs. cuil / legajo / id → read-only (disabled), never patched.
 * Only the declared PerfilUpdate fields are sent (backend uses extra='forbid').
 * < 200 LOC. Submit logic lives in the parent page (onSubmit prop).
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import type { PerfilRead, PerfilUpdate } from '../types'

const schema = z.object({
  nombre: z.string().min(1, 'Obligatorio'),
  apellidos: z.string().min(1, 'Obligatorio'),
  email: z.string().min(1, 'El email no puede estar vacío').email('Email no válido'),
  dni: z.string(),
  genero: z.string(),
  banco: z.string(),
  cbu: z.string(),
  alias_cbu: z.string(),
  regional: z.string(),
  legajo_profesional: z.string(),
  facturador: z.boolean(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  perfil: PerfilRead
  onSubmit: (body: PerfilUpdate) => void
  isSubmitting: boolean
}

/** Maps a PerfilRead into the form's editable defaults (null → ''). */
function toDefaults(p: PerfilRead): FormValues {
  return {
    nombre: p.nombre,
    apellidos: p.apellidos,
    email: p.email,
    dni: p.dni ?? '',
    genero: p.genero ?? '',
    banco: p.banco ?? '',
    cbu: p.cbu ?? '',
    alias_cbu: p.alias_cbu ?? '',
    regional: p.regional ?? '',
    legajo_profesional: p.legajo_profesional ?? '',
    facturador: p.facturador,
  }
}

/** Empty string → null for nullable fields; trimmed email stays a string. */
function toBody(v: FormValues): PerfilUpdate {
  const orNull = (s: string): string | null => (s.trim() === '' ? null : s.trim())
  return {
    nombre: v.nombre.trim(),
    apellidos: v.apellidos.trim(),
    email: v.email.trim(),
    dni: orNull(v.dni),
    genero: orNull(v.genero),
    banco: orNull(v.banco),
    cbu: orNull(v.cbu),
    alias_cbu: orNull(v.alias_cbu),
    regional: orNull(v.regional),
    legajo_profesional: orNull(v.legajo_profesional),
    facturador: v.facturador,
  }
}

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-500'

interface FieldDef {
  name: keyof Omit<FormValues, 'facturador'>
  label: string
}

const TEXT_FIELDS: FieldDef[] = [
  { name: 'nombre', label: 'Nombre' },
  { name: 'apellidos', label: 'Apellidos' },
  { name: 'email', label: 'Email' },
  { name: 'dni', label: 'DNI' },
  { name: 'genero', label: 'Género' },
  { name: 'banco', label: 'Banco' },
  { name: 'cbu', label: 'CBU' },
  { name: 'alias_cbu', label: 'Alias CBU' },
  { name: 'regional', label: 'Regional' },
  { name: 'legajo_profesional', label: 'Legajo profesional' },
]

export default function PerfilForm({ perfil, onSubmit, isSubmitting }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: toDefaults(perfil) })

  return (
    <form onSubmit={handleSubmit((v) => onSubmit(toBody(v)))} className="space-y-4 max-w-2xl">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {TEXT_FIELDS.map((f) => (
          <div key={f.name}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{f.label}</label>
            <input
              {...register(f.name)}
              data-testid={`perfil-${f.name}`}
              className={inputClass}
            />
            {errors[f.name] && (
              <p className="mt-1 text-xs text-red-600">{errors[f.name]?.message}</p>
            )}
          </div>
        ))}

        {/* Read-only identity fields — shown disabled, never patched */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CUIL (solo lectura)</label>
          <input
            data-testid="perfil-cuil"
            value={perfil.cuil ?? ''}
            disabled
            readOnly
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Legajo (solo lectura)</label>
          <input
            data-testid="perfil-legajo"
            value={perfil.legajo ?? ''}
            disabled
            readOnly
            className={inputClass}
          />
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
        <input type="checkbox" {...register('facturador')} data-testid="perfil-facturador" />
        Facturador
      </label>

      <Button type="submit" data-testid="perfil-submit" isLoading={isSubmitting} disabled={isSubmitting}>
        Guardar cambios
      </Button>
    </form>
  )
}
