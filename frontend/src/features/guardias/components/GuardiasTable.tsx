/**
 * GuardiasTable — displays a list of GuardiaRead rows with filters.
 * Filters are controlled by the parent (onFilter / onClear) so the page owns the state.
 * < 200 LOC. Tailwind only.
 */
import { useState } from 'react'
import type { GuardiaRead, GuardiaFiltros, DiaSemana, GuardiaEstado } from '../types'
import { DIAS_SEMANA, GUARDIA_ESTADOS } from '../types'
import { Button, EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  guardias: GuardiaRead[]
  onFilter: (filtros: GuardiaFiltros) => void
  onClear: () => void
}

const selectClass =
  'rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

export default function GuardiasTable({ guardias, onFilter, onClear }: Props) {
  const [dia, setDia] = useState<DiaSemana | ''>('')
  const [estado, setEstado] = useState<GuardiaEstado | ''>('')

  function handleFilter() {
    onFilter({ dia: dia || null, estado: estado || null })
  }

  function handleClear() {
    setDia('')
    setEstado('')
    onClear()
  }

  return (
    <div className="space-y-4">
      <div data-testid="guardias-filters" className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600" htmlFor="filtro-dia">
            Día
          </label>
          <select
            id="filtro-dia"
            value={dia}
            onChange={(e) => setDia(e.target.value as DiaSemana | '')}
            className={selectClass}
          >
            <option value="">Todos</option>
            {DIAS_SEMANA.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600" htmlFor="filtro-estado">
            Estado
          </label>
          <select
            id="filtro-estado"
            value={estado}
            onChange={(e) => setEstado(e.target.value as GuardiaEstado | '')}
            className={selectClass}
          >
            <option value="">Todos</option>
            {GUARDIA_ESTADOS.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>

        <Button variant="primary" size="sm" onClick={handleFilter}>
          Filtrar
        </Button>
        <Button variant="secondary" size="sm" onClick={handleClear}>
          Limpiar filtros
        </Button>
      </div>

      {guardias.length === 0 ? (
        <div data-testid="guardias-empty">
          <EmptyState title="No hay guardias para los filtros aplicados." />
        </div>
      ) : (
        <div data-testid="guardias-table" className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Día
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Horario
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Estado
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Comentarios
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {guardias.map((g) => (
                <tr key={g.id}>
                  <td className="px-4 py-3 text-gray-900">{g.dia}</td>
                  <td className="px-4 py-3 text-gray-700">{g.horario}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={g.estado.toLowerCase()} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{g.comentarios || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
