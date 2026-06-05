/**
 * AvisoForm — React Hook Form + Zod for POST /avisos and PUT /avisos/{id}.
 * Task 2.7. < 200 LOC.
 */
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { avisoFormSchema, type AvisoFormValues } from '../services/avisosService'
import { useCrearAviso, useActualizarAviso } from '../hooks/avisosHooks'
import type { AvisoRead, AvisoAlcance, AvisoSeveridad } from '../types'

interface Props {
  editing?: AvisoRead
  onClose?: () => void
}

const ALCANCE_OPTIONS: AvisoAlcance[] = ['Global', 'PorMateria', 'PorCohorte', 'PorRol']
const SEVERIDAD_OPTIONS: AvisoSeveridad[] = ['Info', 'Advertencia', 'Critico']

export default function AvisoForm({ editing, onClose }: Props) {
  const crearMutation = useCrearAviso()
  const actualizarMutation = useActualizarAviso()
  const isPending = crearMutation.isPending || actualizarMutation.isPending

  const {
    register, handleSubmit, watch, reset, formState: { errors },
  } = useForm<AvisoFormValues>({
    resolver: zodResolver(avisoFormSchema),
    defaultValues: editing
      ? {
          alcance: editing.alcance,
          materia_id: editing.materia_id ?? '',
          cohorte_id: editing.cohorte_id ?? '',
          rol_destino: editing.rol_destino ?? '',
          severidad: editing.severidad,
          titulo: editing.titulo,
          cuerpo: editing.cuerpo,
          inicio_en: editing.inicio_en,
          fin_en: editing.fin_en,
          orden: editing.orden,
          activo: editing.activo,
          requiere_ack: editing.requiere_ack,
        }
      : { alcance: 'Global', severidad: 'Info', orden: 100, activo: true, requiere_ack: false },
  })

  const alcance = watch('alcance')

  useEffect(() => {
    if (editing) reset({ ...editing, materia_id: editing.materia_id ?? '' })
  }, [editing, reset])

  function onSubmit(values: AvisoFormValues) {
    const body = {
      ...values,
      materia_id: values.materia_id || null,
      cohorte_id: values.cohorte_id || null,
      rol_destino: values.rol_destino || null,
    }

    if (editing) {
      actualizarMutation.mutate(
        { id: editing.id, body },
        {
          onSuccess: () => { toast.success('Aviso actualizado'); onClose?.() },
          onError: (err) => toast.error((err as { detail?: string }).detail ?? 'Error'),
        },
      )
    } else {
      crearMutation.mutate(body, {
        onSuccess: () => { toast.success('Aviso publicado'); reset(); onClose?.() },
        onError: (err) => toast.error((err as { detail?: string }).detail ?? 'Error'),
      })
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <h3 className="font-medium text-gray-800">{editing ? 'Editar aviso' : 'Nuevo aviso'}</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Alcance</label>
          <select {...register('alcance')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
            {ALCANCE_OPTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Severidad</label>
          <select {...register('severidad')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
            {SEVERIDAD_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {alcance === 'PorMateria' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Materia ID</label>
          <input {...register('materia_id')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.materia_id && <p className="mt-1 text-xs text-red-600">{errors.materia_id.message}</p>}
        </div>
      )}
      {alcance === 'PorCohorte' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cohorte ID</label>
          <input {...register('cohorte_id')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.cohorte_id && <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>}
        </div>
      )}
      {alcance === 'PorRol' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Rol destino</label>
          <input {...register('rol_destino')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.rol_destino && <p className="mt-1 text-xs text-red-600">{errors.rol_destino.message}</p>}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
        <input {...register('titulo')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        {errors.titulo && <p className="mt-1 text-xs text-red-600">{errors.titulo.message}</p>}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Cuerpo</label>
        <textarea {...register('cuerpo')} rows={3} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        {errors.cuerpo && <p className="mt-1 text-xs text-red-600">{errors.cuerpo.message}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Inicio</label>
          <input type="datetime-local" {...register('inicio_en')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.inicio_en && <p className="mt-1 text-xs text-red-600">{errors.inicio_en.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fin</label>
          <input type="datetime-local" {...register('fin_en')} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.fin_en && <p className="mt-1 text-xs text-red-600">{errors.fin_en.message}</p>}
        </div>
      </div>
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('activo')} />
          Activo
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('requiere_ack')} />
          Requiere confirmación
        </label>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={isPending} className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
          {isPending ? 'Guardando…' : editing ? 'Actualizar' : 'Publicar'}
        </button>
        {onClose && (
          <button type="button" onClick={onClose} className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50">
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
