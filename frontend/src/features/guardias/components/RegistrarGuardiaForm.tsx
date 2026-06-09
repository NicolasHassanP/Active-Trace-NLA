/**
 * RegistrarGuardiaForm — React Hook Form + Zod form for POST /api/v1/guardias.
 *
 * The (materia, carrera, cohorte) tripleta is chosen from the user's own
 * assignments (GET /equipos/mis-equipos via useMisEquipos) — never typed by hand
 * and never sent as asignacion_id/tenant_id (those come from the JWT on the backend).
 *
 * Submit logic lives in the parent page (onSubmit prop). < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui'
import type { MisEquiposItem } from '@/features/equipos/types'
import type { RegistrarGuardiaRequest, DiaSemana, GuardiaEstado } from '../types'
import { DIAS_SEMANA, GUARDIA_ESTADOS } from '../types'

const DIAS = DIAS_SEMANA as [DiaSemana, ...DiaSemana[]]
const ESTADOS = GUARDIA_ESTADOS as [GuardiaEstado, ...GuardiaEstado[]]

const schema = z.object({
  // tripleta_key encodes materia/carrera/cohorte as a single selected option
  tripleta_key: z.string().min(1, 'Seleccioná una asignación'),
  dia: z.enum(DIAS),
  horario: z.string().min(1, 'Obligatorio'),
  estado: z.enum(ESTADOS),
  comentarios: z.string(),
})

type FormValues = z.infer<typeof schema>

interface TripletaOption {
  key: string
  materia_id: string
  carrera_id: string
  cohorte_id: string
  label: string
}

interface Props {
  asignaciones: MisEquiposItem[]
  onSubmit: (body: RegistrarGuardiaRequest) => void
  isSubmitting: boolean
}

/** Builds unique tripleta options from the user's assignments (those with full tripleta). */
function buildTripletas(asignaciones: MisEquiposItem[]): TripletaOption[] {
  const seen = new Set<string>()
  const out: TripletaOption[] = []
  for (const a of asignaciones) {
    if (!a.materia_id || !a.carrera_id || !a.cohorte_id) continue
    const key = `${a.materia_id}|${a.carrera_id}|${a.cohorte_id}`
    if (seen.has(key)) continue
    seen.add(key)
    const label = [a.materia_nombre ?? a.materia_id, a.carrera_nombre, a.cohorte_nombre]
      .filter(Boolean)
      .join(' · ')
    out.push({
      key,
      materia_id: a.materia_id,
      carrera_id: a.carrera_id,
      cohorte_id: a.cohorte_id,
      label,
    })
  }
  return out
}

const inputClass = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'

export default function RegistrarGuardiaForm({ asignaciones, onSubmit, isSubmitting }: Props) {
  const tripletas = buildTripletas(asignaciones)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { tripleta_key: '', dia: 'Lunes', horario: '', estado: 'Pendiente', comentarios: '' },
  })

  function submit(values: FormValues) {
    const tripleta = tripletas.find((t) => t.key === values.tripleta_key)
    if (!tripleta) return
    onSubmit({
      materia_id: tripleta.materia_id,
      carrera_id: tripleta.carrera_id,
      cohorte_id: tripleta.cohorte_id,
      dia: values.dia,
      horario: values.horario.trim(),
      estado: values.estado,
      comentarios: values.comentarios.trim(),
    })
    reset()
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="max-w-2xl space-y-4" data-testid="registrar-guardia-form">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Materia · Carrera · Cohorte</label>
        <select {...register('tripleta_key')} data-testid="guardia-tripleta" className={inputClass}>
          <option value="">Seleccioná una asignación…</option>
          {tripletas.map((t) => (
            <option key={t.key} value={t.key}>
              {t.label}
            </option>
          ))}
        </select>
        {errors.tripleta_key && <p className="mt-1 text-xs text-red-600">{errors.tripleta_key.message}</p>}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Día</label>
          <select {...register('dia')} data-testid="guardia-dia" className={inputClass}>
            {DIAS_SEMANA.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Horario</label>
          <input
            {...register('horario')}
            data-testid="guardia-horario"
            placeholder="10:00-12:00"
            className={inputClass}
          />
          {errors.horario && <p className="mt-1 text-xs text-red-600">{errors.horario.message}</p>}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Estado</label>
          <select {...register('estado')} data-testid="guardia-estado" className={inputClass}>
            {GUARDIA_ESTADOS.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Comentarios</label>
        <textarea
          {...register('comentarios')}
          data-testid="guardia-comentarios"
          rows={2}
          className={inputClass}
        />
      </div>

      <Button type="submit" data-testid="guardia-submit" isLoading={isSubmitting} disabled={isSubmitting}>
        Registrar guardia
      </Button>
    </form>
  )
}
