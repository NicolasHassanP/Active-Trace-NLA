/**
 * PasoProgramas — Step 5: Load materia program references.
 * Task 7.8. Uses setupCuatrimestreService.crearPrograma + programaCreateSchema (Zod).
 * materia_id / carrera_id / cohorte_id → <select> by nombre (useEstructuraOptions).
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { crearPrograma, programaCreateSchema } from '../services/setupCuatrimestreService'
import type { ProgramaFormValues } from '../services/setupCuatrimestreService'
import { parseDomainError } from '@/shared/services/domainError'
import { Button } from '@/shared/components/ui'
import { useEstructuraOptions } from '../hooks/useEstructuraOptions'

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoProgramas({ onSuccess, onError }: Props) {
  const { materias, carreras, cohortes, isLoading } = useEstructuraOptions()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProgramaFormValues>({ resolver: zodResolver(programaCreateSchema) })

  async function onSubmit(data: ProgramaFormValues) {
    try {
      await crearPrograma(data)
      onSuccess()
    } catch (err) {
      const de = parseDomainError(err)
      onError(de.detail)
    }
  }

  const inputClass =
    'mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400'

  const placeholder = isLoading ? 'Cargando…' : '-- Seleccioná --'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-programas">
      <p className="text-sm text-gray-600">
        Registrá la referencia del programa de la materia para este cuatrimestre.
      </p>

      <div className="grid grid-cols-3 gap-3">
        {/* Materia — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Materia</label>
          <select
            {...register('materia_id')}
            className={inputClass}
            data-testid="programas-materia-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>{m.nombre}</option>
            ))}
          </select>
          {errors.materia_id && (
            <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>
          )}
        </div>

        {/* Carrera — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Carrera</label>
          <select
            {...register('carrera_id')}
            className={inputClass}
            data-testid="programas-carrera-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {carreras.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.carrera_id && (
            <p className="mt-1 text-xs text-red-600">{errors.carrera_id.message}</p>
          )}
        </div>

        {/* Cohorte — select by nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Cohorte</label>
          <select
            {...register('cohorte_id')}
            className={inputClass}
            data-testid="programas-cohorte-id"
            disabled={isLoading}
          >
            <option value="">{placeholder}</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {errors.cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Título del programa</label>
        <input
          {...register('titulo')}
          className={inputClass}
          placeholder="ej. Programa Cálculo I 2026"
        />
        {errors.titulo && (
          <p className="mt-1 text-xs text-red-600">{errors.titulo.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Referencia de archivo</label>
        <input
          {...register('referencia_archivo')}
          className={inputClass}
          placeholder="ej. s3://bucket/programa.pdf"
        />
        {errors.referencia_archivo && (
          <p className="mt-1 text-xs text-red-600">{errors.referencia_archivo.message}</p>
        )}
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
        {isSubmitting ? 'Cargando…' : 'Registrar programa'}
      </Button>
    </form>
  )
}
