/**
 * PasoFechas — Step 6: Load academic evaluation dates.
 * Task 7.9. Uses setupCuatrimestreService.crearFechaAcademica + fechaAcademicaCreateSchema.
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  crearFechaAcademica,
  fechaAcademicaCreateSchema,
} from '../services/setupCuatrimestreService'
import type { FechaAcademicaFormValues } from '../services/setupCuatrimestreService'
import { parseDomainError } from '@/shared/services/domainError'
import type { FechaAcademicaTipo } from '../types'
import { Button } from '@/shared/components/ui'

const TIPO_OPTIONS: FechaAcademicaTipo[] = [
  'Parcial',
  'RecuperatorioParcial',
  'Integrador',
  'RecuperatorioIntegrador',
  'ColoquioEscrito',
  'ColoquioOral',
  'TrabajoPractico',
  'ExamenFinal',
]

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoFechas({ onSuccess, onError }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FechaAcademicaFormValues>({ resolver: zodResolver(fechaAcademicaCreateSchema) })

  async function onSubmit(data: FechaAcademicaFormValues) {
    try {
      await crearFechaAcademica({
        ...data,
        numero: Number(data.numero),
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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-fechas">
      <p className="text-sm text-gray-600">
        Registrá las fechas de evaluación del cuatrimestre.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Materia</label>
          <input {...register('materia_id')} className={inputClass} />
          {errors.materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Cohorte</label>
          <input {...register('cohorte_id')} className={inputClass} />
          {errors.cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Tipo</label>
          <select {...register('tipo')} className={inputClass}>
            {TIPO_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          {errors.tipo && <p className="mt-1 text-xs text-red-600">{errors.tipo.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Número</label>
          <input
            {...register('numero', { valueAsNumber: true })}
            type="number"
            min={1}
            className={inputClass}
          />
          {errors.numero && (
            <p className="mt-1 text-xs text-red-600">{errors.numero.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Período (ej. 2026-1)</label>
          <input {...register('periodo')} className={inputClass} placeholder="2026-1" />
          {errors.periodo && (
            <p className="mt-1 text-xs text-red-600">{errors.periodo.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Fecha</label>
          <input {...register('fecha')} type="date" className={inputClass} />
          {errors.fecha && <p className="mt-1 text-xs text-red-600">{errors.fecha.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Título</label>
          <input
            {...register('titulo')}
            className={inputClass}
            placeholder="ej. Primer Parcial"
          />
          {errors.titulo && (
            <p className="mt-1 text-xs text-red-600">{errors.titulo.message}</p>
          )}
        </div>
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
        {isSubmitting ? 'Cargando…' : 'Registrar fecha'}
      </Button>
    </form>
  )
}
