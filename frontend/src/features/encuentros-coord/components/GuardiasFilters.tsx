/**
 * GuardiasFilters — filter controls for the guardias list.
 * Task 5.6. < 200 LOC. Tailwind only.
 */
import { useState } from 'react'
import type { GuardiaParams } from '../types'

const DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
const ESTADOS = ['Pendiente', 'Realizada', 'Cancelada']

interface Props {
  onFilter: (params: GuardiaParams) => void
  onClear: () => void
}

export default function GuardiasFilters({ onFilter, onClear }: Props) {
  const [dia, setDia] = useState('')
  const [estado, setEstado] = useState('')

  function handleFilter() {
    onFilter({
      dia: dia || null,
      estado: estado || null,
    })
  }

  function handleClear() {
    setDia('')
    setEstado('')
    onClear()
  }

  return (
    <div data-testid="guardias-filters" className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="guardia-dia">
          Día
        </label>
        <select
          id="guardia-dia"
          value={dia}
          onChange={(e) => setDia(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos</option>
          {DIAS.map((d) => (
            <option key={d} value={d} className="capitalize">
              {d}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="guardia-estado">
          Estado
        </label>
        <select
          id="guardia-estado"
          value={estado}
          onChange={(e) => setEstado(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos</option>
          {ESTADOS.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={handleFilter}
        className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700"
      >
        Filtrar
      </button>
      <button
        type="button"
        onClick={handleClear}
        className="rounded border border-gray-300 px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
      >
        Limpiar filtros
      </button>
    </div>
  )
}
