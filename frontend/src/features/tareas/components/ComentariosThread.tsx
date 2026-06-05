/**
 * ComentariosThread — displays + adds comments for a Tarea.
 * Task 3.7. < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useComentariosTarea, useAgregarComentario } from '../hooks/tareasHooks'

interface Props {
  tareaId: string
}

export default function ComentariosThread({ tareaId }: Props) {
  const comentariosQuery = useComentariosTarea(tareaId)
  const agregarMutation = useAgregarComentario()
  const [cuerpo, setCuerpo] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!cuerpo.trim()) return
    agregarMutation.mutate(
      { tareaId, body: { cuerpo: cuerpo.trim() } },
      {
        onSuccess: () => {
          toast.success('Comentario agregado')
          setCuerpo('')
        },
        onError: (err) => toast.error((err as { detail?: string }).detail ?? 'Error al agregar comentario'),
      },
    )
  }

  const comentarios = comentariosQuery.data ?? []

  return (
    <div data-testid="comentarios-thread" className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-700">Comentarios</h3>

      {comentariosQuery.isLoading && (
        <p className="text-xs text-gray-400">Cargando comentarios…</p>
      )}

      {comentariosQuery.isError && (
        <p role="alert" className="text-xs text-red-500">Error al cargar los comentarios.</p>
      )}

      {!comentariosQuery.isLoading && comentarios.length === 0 && (
        <p className="text-xs text-gray-400">Sin comentarios.</p>
      )}

      <ul className="space-y-2">
        {comentarios.map((c) => (
          <li key={c.id} className={`rounded p-3 text-sm ${c.es_sistema ? 'bg-yellow-50 text-yellow-700 italic' : 'bg-gray-50 text-gray-800'}`}>
            <p>{c.cuerpo}</p>
            <p className="mt-1 text-xs text-gray-400">{new Date(c.created_at).toLocaleString()}</p>
          </li>
        ))}
      </ul>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={cuerpo}
          onChange={(e) => setCuerpo(e.target.value)}
          placeholder="Agregar comentario…"
          className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={agregarMutation.isPending || !cuerpo.trim()}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {agregarMutation.isPending ? '…' : 'Enviar'}
        </button>
      </form>
    </div>
  )
}
