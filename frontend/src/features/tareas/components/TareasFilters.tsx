/**
 * TareasFilters — filter bar for the admin tasks panel.
 * Task 3.7. < 200 LOC.
 */
import { useState } from 'react'
import type { TareasAdminParams, TareaEstado } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  onFilter: (params: TareasAdminParams) => void
}

const ESTADOS: TareaEstado[] = ['Pendiente', 'EnProgreso', 'Resuelta', 'Cancelada']

export default function TareasFilters({ onFilter }: Props) {
  const [asignadoA, setAsignadoA] = useState('')
  const [materiaId, setMateriaId] = useState('')
  const [estado, setEstado] = useState<TareaEstado | ''>('')
  const [q, setQ] = useState('')

  function handleApply() {
    onFilter({
      asignado_a: asignadoA || null,
      materia_id: materiaId || null,
      estado: (estado as TareaEstado) || null,
      q: q || null,
    })
  }

  function handleClear() {
    setAsignadoA('')
    setMateriaId('')
    setEstado('')
    setQ('')
    onFilter({})
  }

  return (
    <div data-testid="tareas-filters" className="flex flex-wrap gap-3">
      <input
        type="text"
        placeholder="ID docente asignado"
        value={asignadoA}
        onChange={(e) => setAsignadoA(e.target.value)}
        className="rounded border border-gray-300 px-3 py-1.5 text-sm"
      />
      <input
        type="text"
        placeholder="ID materia"
        value={materiaId}
        onChange={(e) => setMateriaId(e.target.value)}
        className="rounded border border-gray-300 px-3 py-1.5 text-sm"
      />
      <select
        value={estado}
        onChange={(e) => setEstado(e.target.value as TareaEstado | '')}
        className="rounded border border-gray-300 px-3 py-1.5 text-sm"
      >
        <option value="">Todos los estados</option>
        {ESTADOS.map((e) => (
          <option key={e} value={e}>{e}</option>
        ))}
      </select>
      <input
        type="text"
        placeholder="Búsqueda libre"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="rounded border border-gray-300 px-3 py-1.5 text-sm"
      />
      <Button variant="primary" size="sm" onClick={handleApply}>
        Filtrar
      </Button>
      <Button variant="secondary" size="sm" onClick={handleClear}>
        Limpiar
      </Button>
    </div>
  )
}
