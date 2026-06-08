/**
 * CrearSlotDialog — modal form to create a slot de encuentro.
 * Two modes: único (fecha_unica) or recurrente (dia_semana + fecha_inicio + cant_semanas).
 * < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useCrearSlot } from '../hooks/encuentrosCoordHooks'
import type { SlotModo } from '../types'

const DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'] as const

interface Props {
  materiaId: string
  materiaNombre: string
  onClose: () => void
}

interface FormState {
  titulo: string
  hora: string
  modo: SlotModo
  fecha_unica: string
  dia_semana: string
  fecha_inicio: string
  cant_semanas: number
  meet_url: string
}

const EMPTY: FormState = {
  titulo: '',
  hora: '18:00',
  modo: 'unico',
  fecha_unica: '',
  dia_semana: 'lunes',
  fecha_inicio: '',
  cant_semanas: 4,
  meet_url: '',
}

export default function CrearSlotDialog({ materiaId, materiaNombre, onClose }: Props) {
  const [form, setForm] = useState<FormState>(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const mutation = useCrearSlot()

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!form.titulo.trim()) { setError('El título es obligatorio.'); return }
    if (!form.hora) { setError('La hora es obligatoria.'); return }

    const payload =
      form.modo === 'unico'
        ? {
            materia_id: materiaId,
            titulo: form.titulo.trim(),
            hora: form.hora,
            cant_semanas: 0,
            fecha_unica: form.fecha_unica || null,
            meet_url: form.meet_url || null,
          }
        : {
            materia_id: materiaId,
            titulo: form.titulo.trim(),
            hora: form.hora,
            cant_semanas: form.cant_semanas,
            dia_semana: form.dia_semana,
            fecha_inicio: form.fecha_inicio || null,
            meet_url: form.meet_url || null,
          }

    try {
      const res = await mutation.mutateAsync(payload)
      // success — close and let the query invalidation refresh the table
      toast.success(`Encuentro creado: ${res.instancias.length} instancia(s) generadas`)
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al crear el slot.'
      setError(msg)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Nuevo encuentro</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4 px-6 py-5">
          {/* Materia (read-only context) */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Materia</label>
            <p className="text-sm text-gray-800 font-medium">{materiaNombre}</p>
          </div>

          {/* Título */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Título *</label>
            <input
              type="text"
              value={form.titulo}
              onChange={(e) => set('titulo', e.target.value)}
              placeholder="Ej: Clase sincrónica semana 1"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Hora */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Hora *</label>
            <input
              type="time"
              value={form.hora}
              onChange={(e) => set('hora', e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Meet URL */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">URL de Meet (opcional)</label>
            <input
              type="url"
              value={form.meet_url}
              onChange={(e) => set('meet_url', e.target.value)}
              placeholder="https://meet.google.com/..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Modo */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tipo de slot</label>
            <div className="flex gap-4">
              {(['unico', 'recurrente'] as SlotModo[]).map((m) => (
                <label key={m} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="radio"
                    checked={form.modo === m}
                    onChange={() => set('modo', m)}
                    className="accent-indigo-600"
                  />
                  {m === 'unico' ? 'Único' : 'Recurrente'}
                </label>
              ))}
            </div>
          </div>

          {/* Único */}
          {form.modo === 'unico' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Fecha</label>
              <input
                type="date"
                value={form.fecha_unica}
                onChange={(e) => set('fecha_unica', e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}

          {/* Recurrente */}
          {form.modo === 'recurrente' && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Día de semana</label>
                <select
                  value={form.dia_semana}
                  onChange={(e) => set('dia_semana', e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {DIAS.map((d) => (
                    <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Fecha de inicio</label>
                <input
                  type="date"
                  value={form.fecha_inicio}
                  onChange={(e) => set('fecha_inicio', e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Cantidad de semanas (1–52)</label>
                <input
                  type="number"
                  min={1}
                  max={52}
                  value={form.cant_semanas}
                  onChange={(e) => set('cant_semanas', Number(e.target.value))}
                  className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {mutation.isPending ? 'Creando…' : 'Crear slot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
