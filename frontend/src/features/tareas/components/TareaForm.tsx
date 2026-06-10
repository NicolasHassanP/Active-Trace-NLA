/**
 * TareaForm — form for creating a new Tarea.
 * Docente selector from GET /equipos/mis-equipos (uses user's team context).
 * Materia selector from GET /perfil/mis-asignaciones.
 * Task 3.7. < 200 LOC.
 */
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'
import { listarMisEquipos, consultarEquipo } from '@/features/equipos/services/equiposService'
import { useCrearTarea } from '../hooks/tareasHooks'

interface Props {
  onClose: () => void
}

function docenteLabel(item: { usuario_nombre: string | null; usuario_apellidos: string | null; usuario_id: string; rol: string }): string {
  const nombre = [item.usuario_apellidos, item.usuario_nombre].filter(Boolean).join(', ')
  return nombre ? `${nombre} (${item.rol})` : `${item.usuario_id.slice(0, 8)}… (${item.rol})`
}

export default function TareaForm({ onClose }: Props) {
  const crearMutation = useCrearTarea()

  const [asignadoA, setAsignadoA] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [materiaId, setMateriaId] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Load coordinator's own asignaciones to get materia context
  const misEquiposQuery = useQuery({
    queryKey: ['mis-equipos-form'],
    queryFn: listarMisEquipos,
  })

  const misAsignacionesQuery = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
  })

  // Get first available materia/carrera/cohorte from coordinator's assignments
  const misEquipos = misEquiposQuery.data ?? []
  const uniqueMaterias = misEquipos.filter(
    (a, i, arr) => a.materia_id && arr.findIndex((b) => b.materia_id === a.materia_id) === i,
  )
  const selectedEquipoContext = misEquipos.find((e) => e.materia_id === materiaId)

  // Load team members for selected materia context
  const equipoQuery = useQuery({
    queryKey: ['equipo-docentes', selectedEquipoContext?.materia_id, selectedEquipoContext?.carrera_id, selectedEquipoContext?.cohorte_id],
    queryFn: () =>
      consultarEquipo({
        materia_id: selectedEquipoContext!.materia_id!,
        carrera_id: selectedEquipoContext!.carrera_id!,
        cohorte_id: selectedEquipoContext!.cohorte_id!,
      }),
    enabled: !!(selectedEquipoContext?.materia_id && selectedEquipoContext?.carrera_id && selectedEquipoContext?.cohorte_id),
  })

  // Reset docente when materia changes
  useEffect(() => { setAsignadoA('') }, [materiaId])

  const docentes = equipoQuery.data ?? []
  const misAsignaciones = misAsignacionesQuery.data ?? []

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!asignadoA) { setError('Seleccioná un docente.'); return }
    if (!descripcion.trim()) { setError('La descripción es obligatoria.'); return }

    crearMutation.mutate(
      {
        asignado_a: asignadoA,
        descripcion: descripcion.trim(),
        materia_id: materiaId || null,
        contexto_id: null,
        contexto_tipo: null,
      },
      {
        onSuccess: () => {
          toast.success('Tarea creada correctamente')
          onClose()
        },
        onError: (err) => {
          toast.error((err as { detail?: string }).detail ?? 'Error al crear la tarea')
        },
      },
    )
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">

      {/* Materia (context para cargar equipo) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Materia (opcional)
        </label>
        <select
          value={materiaId}
          onChange={(e) => setMateriaId(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">Sin materia asignada</option>
          {uniqueMaterias.map((e) => (
            <option key={e.materia_id!} value={e.materia_id!}>
              {e.materia_nombre ?? e.materia_id}
            </option>
          ))}
          {misAsignaciones
            .filter((a) => a.materia_id && !uniqueMaterias.some((e) => e.materia_id === a.materia_id))
            .map((a) => (
              <option key={a.materia_id!} value={a.materia_id!}>
                {a.materia_nombre ?? a.materia_id}
              </option>
            ))}
        </select>
      </div>

      {/* Docente asignado */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Docente asignado <span className="text-red-500">*</span>
        </label>
        {!materiaId ? (
          <p className="text-xs text-gray-400 italic">Seleccioná una materia para ver el equipo disponible.</p>
        ) : equipoQuery.isLoading ? (
          <p className="text-xs text-gray-400">Cargando equipo…</p>
        ) : docentes.length === 0 ? (
          <p className="text-xs text-amber-600">No hay docentes en el equipo para esta materia.</p>
        ) : (
          <select
            value={asignadoA}
            onChange={(e) => setAsignadoA(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">-- Seleccioná un docente --</option>
            {docentes.map((d) => (
              <option key={d.asignacion_id} value={d.usuario_id}>
                {docenteLabel(d)}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Descripción */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Descripción <span className="text-red-500">*</span>
        </label>
        <textarea
          rows={3}
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          placeholder="Describí la tarea a realizar…"
        />
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={crearMutation.isPending}
          className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {crearMutation.isPending ? 'Creando…' : 'Crear tarea'}
        </button>
      </div>
    </form>
  )
}
