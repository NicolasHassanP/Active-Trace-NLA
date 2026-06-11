/**
 * TareasFilters — filter bar for the admin tasks panel.
 * Task 3.7. < 200 LOC.
 *
 * Governance note:
 *   This component is only rendered for COORDINADOR / ADMIN roles (see TareasPage).
 *   Both roles hold the 'equipos:asignar' permission, so using UsuarioCombobox
 *   (backed by GET /asignaciones/usuarios) is safe — no 403 risk.
 *   The 'asignado_a' filter uses the default useBuscarUsuariosAsignables hook.
 *
 * Materia filter uses a <select> from listarMisEquipos + getMisAsignaciones,
 * matching the same pattern as TareaForm — no extra permission needed.
 */
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { TareasAdminParams, TareaEstado } from '../types'
import { Button } from '@/shared/components/ui'
import UsuarioCombobox from '@/features/asignaciones/components/UsuarioCombobox'
import { listarMisEquipos } from '@/features/equipos/services/equiposService'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'

interface Props {
  onFilter: (params: TareasAdminParams) => void
}

const ESTADOS: TareaEstado[] = ['Pendiente', 'EnProgreso', 'Resuelta', 'Cancelada']

export default function TareasFilters({ onFilter }: Props) {
  const [asignadoA, setAsignadoA] = useState<string | null>(null)
  const [materiaId, setMateriaId] = useState('')
  const [estado, setEstado] = useState<TareaEstado | ''>('')
  const [q, setQ] = useState('')

  // Load materias from the coordinator's equipo context (same pattern as TareaForm)
  const misEquiposQuery = useQuery({
    queryKey: ['mis-equipos-filters'],
    queryFn: listarMisEquipos,
  })
  const misAsignacionesQuery = useQuery({
    queryKey: ['mis-asignaciones-filters'],
    queryFn: getMisAsignaciones,
  })

  const misEquipos = misEquiposQuery.data ?? []
  const misAsignaciones = misAsignacionesQuery.data ?? []

  // Deduplicated materia list across both sources
  const uniqueMaterias = misEquipos.filter(
    (a, i, arr) => a.materia_id && arr.findIndex((b) => b.materia_id === a.materia_id) === i,
  )
  const extraMaterias = misAsignaciones.filter(
    (a) => a.materia_id && !uniqueMaterias.some((e) => e.materia_id === a.materia_id),
  )

  function handleApply() {
    onFilter({
      asignado_a: asignadoA || null,
      materia_id: materiaId || null,
      estado: (estado as TareaEstado) || null,
      q: q || null,
    })
  }

  function handleClear() {
    setAsignadoA(null)
    setMateriaId('')
    setEstado('')
    setQ('')
    onFilter({})
  }

  // When asignadoA changes (combobox cleared) propagate reactively
  useEffect(() => {
    // intentionally no-op: user triggers filter via button
  }, [asignadoA])

  return (
    <div data-testid="tareas-filters" className="flex flex-wrap gap-3 items-end">
      {/* Docente asignado — UsuarioCombobox (safe: COORDINADOR/ADMIN have equipos:asignar) */}
      <div className="min-w-[220px] max-w-xs flex-1">
        <label className="mb-1 block text-xs font-medium text-gray-600">Docente asignado</label>
        <UsuarioCombobox
          value={asignadoA}
          onChange={(id) => setAsignadoA(id)}
        />
      </div>

      {/* Materia — select por nombre (mismo patrón que TareaForm) */}
      <div className="min-w-[180px] flex-1">
        <label className="mb-1 block text-xs font-medium text-gray-600">Materia</label>
        <select
          data-testid="filtro-materia"
          value={materiaId}
          onChange={(e) => setMateriaId(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Todas las materias</option>
          {uniqueMaterias.map((e) => (
            <option key={e.materia_id!} value={e.materia_id!}>
              {e.materia_nombre ?? e.materia_id}
            </option>
          ))}
          {extraMaterias.map((a) => (
            <option key={a.materia_id!} value={a.materia_id!}>
              {a.materia_nombre ?? a.materia_id}
            </option>
          ))}
        </select>
      </div>

      {/* Estado */}
      <div className="min-w-[160px]">
        <label className="mb-1 block text-xs font-medium text-gray-600">Estado</label>
        <select
          value={estado}
          onChange={(e) => setEstado(e.target.value as TareaEstado | '')}
          className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Todos los estados</option>
          {ESTADOS.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
      </div>

      {/* Búsqueda libre */}
      <div className="min-w-[160px] flex-1">
        <label className="mb-1 block text-xs font-medium text-gray-600">Búsqueda libre</label>
        <input
          type="text"
          placeholder="Buscar..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>

      <div className="flex gap-2">
        <Button variant="primary" size="sm" onClick={handleApply}>
          Filtrar
        </Button>
        <Button variant="secondary" size="sm" onClick={handleClear}>
          Limpiar
        </Button>
      </div>
    </div>
  )
}
