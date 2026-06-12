/**
 * AsignacionesFilters — filter bar for the Asignaciones table.
 * All filtering is client-side (in-memory). Filters apply on change (live).
 * Receives options derived from the full list (distinct materias, cohortes).
 * < 200 LOC. Tailwind only.
 */
import type { AsignacionClientFiltros, EstadoVigencia, RolAsignacion } from '../types'
import { ROLES_ASIGNACION, ESTADOS_VIGENCIA } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  filtros: AsignacionClientFiltros
  onChange: (filtros: AsignacionClientFiltros) => void
  onClear: () => void
  /** Distinct materia_nombre values from the full list. */
  materias: string[]
  /** Distinct cohorte_nombre values from the full list. */
  cohortes: string[]
}

const VIGENCIA_LABELS: Record<EstadoVigencia, string> = {
  vigente: 'Vigente',
  vencida: 'Vencida',
  no_iniciada: 'No iniciada',
}

const inputClass =
  'rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

const selectClass = inputClass

export default function AsignacionesFilters({
  filtros,
  onChange,
  onClear,
  materias,
  cohortes,
}: Props) {
  function set<K extends keyof AsignacionClientFiltros>(
    key: K,
    value: AsignacionClientFiltros[K],
  ) {
    onChange({ ...filtros, [key]: value })
  }

  return (
    <div data-testid="asignaciones-filters" className="flex flex-wrap items-end gap-3">
      {/* Usuario — substring text search */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-usuario">
          Usuario
        </label>
        <input
          id="filtro-usuario"
          data-testid="filtro-usuario"
          type="text"
          placeholder="Buscar por nombre…"
          value={filtros.usuario ?? ''}
          onChange={(e) => set('usuario', e.target.value)}
          className={`${inputClass} w-44`}
        />
      </div>

      {/* Rol */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-rol">
          Rol
        </label>
        <select
          id="filtro-rol"
          data-testid="filtro-rol"
          value={filtros.rol ?? ''}
          onChange={(e) => set('rol', e.target.value as RolAsignacion | '')}
          className={selectClass}
        >
          <option value="">Todos</option>
          {ROLES_ASIGNACION.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      {/* Materia */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-materia">
          Materia
        </label>
        <select
          id="filtro-materia"
          data-testid="filtro-materia"
          value={filtros.materia ?? ''}
          onChange={(e) => set('materia', e.target.value)}
          className={selectClass}
        >
          <option value="">Todas</option>
          {materias.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Cohorte */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-cohorte">
          Cohorte
        </label>
        <select
          id="filtro-cohorte"
          data-testid="filtro-cohorte"
          value={filtros.cohorte ?? ''}
          onChange={(e) => set('cohorte', e.target.value)}
          className={selectClass}
        >
          <option value="">Todas</option>
          {cohortes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Vigencia */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-vigencia">
          Vigencia
        </label>
        <select
          id="filtro-vigencia"
          data-testid="filtro-vigencia"
          value={filtros.vigencia ?? ''}
          onChange={(e) => set('vigencia', e.target.value as EstadoVigencia | '')}
          className={selectClass}
        >
          <option value="">Todas</option>
          {ESTADOS_VIGENCIA.map((v) => (
            <option key={v} value={v}>
              {VIGENCIA_LABELS[v]}
            </option>
          ))}
        </select>
      </div>

      {/* Desde */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-desde">
          Desde
        </label>
        <input
          id="filtro-desde"
          data-testid="filtro-desde"
          type="date"
          value={filtros.desde ?? ''}
          onChange={(e) => set('desde', e.target.value)}
          className={inputClass}
        />
      </div>

      {/* Hasta (rango sobre la columna "desde") */}
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-gray-600" htmlFor="filtro-hasta">
          Hasta
        </label>
        <input
          id="filtro-hasta"
          data-testid="filtro-hasta"
          type="date"
          value={filtros.hasta ?? ''}
          onChange={(e) => set('hasta', e.target.value)}
          className={inputClass}
        />
      </div>

      <Button variant="secondary" size="sm" onClick={onClear}>
        Limpiar filtros
      </Button>
    </div>
  )
}
