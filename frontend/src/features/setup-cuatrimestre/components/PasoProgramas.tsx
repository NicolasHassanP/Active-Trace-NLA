/**
 * PasoProgramas — Step 5: Load materia program references.
 * Task 7.8. Uses setupCuatrimestreService.crearPrograma + programaCreateSchema (Zod).
 * < 200 LOC.
 */
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { crearPrograma, programaCreateSchema } from '../services/setupCuatrimestreService'
import type { ProgramaFormValues } from '../services/setupCuatrimestreService'
import { parseDomainError } from '@/shared/services/domainError'

interface Props {
  onSuccess: () => void
  onError: (msg: string) => void
}

export default function PasoProgramas({ onSuccess, onError }: Props) {
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

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="paso-programas">
      <p className="text-sm text-gray-600">
        Registrá la referencia del programa de la materia para este cuatrimestre.
      </p>

      <div className="grid grid-cols-3 gap-3">
        {(['materia_id', 'carrera_id', 'cohorte_id'] as const).map((field) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700">
              {field.replace('_id', '').charAt(0).toUpperCase() +
                field.replace('_id', '').slice(1)}
            </label>
            <input {...register(field)} className={inputClass} />
            {errors[field] && (
              <p className="mt-1 text-xs text-red-600">{errors[field]?.message}</p>
            )}
          </div>
        ))}
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

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Cargando…' : 'Registrar programa'}
      </button>
    </form>
  )
}
