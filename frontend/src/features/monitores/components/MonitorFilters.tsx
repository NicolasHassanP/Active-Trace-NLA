/**
 * MonitorFilters — reactive filter bar for the monitor page.
 * Todos los campos disparan onFilter con debounce 300ms — sin botón Filtrar.
 * materia_id / cohorte_id vienen del selector del padre (MonitorPage).
 * Task 4.5. < 200 LOC.
 */
import { useEffect, useRef, useState } from 'react'
import type { MonitorParams } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  onFilter: (params: MonitorParams) => void
  onClear: () => void
}

const DEBOUNCE_MS = 300

export default function MonitorFilters({ onFilter, onClear }: Props) {
  const [busqueda, setBusqueda] = useState('')
  const [comision, setComision] = useState('')
  const [regional, setRegional] = useState('')
  const [actividad, setActividad] = useState('')
  const [minCumplidas, setMinCumplidas] = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function fire(overrides: Partial<MonitorParams> = {}) {
    if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      onFilter({
        busqueda: busqueda || null,
        comision: comision || null,
        regional: regional || null,
        actividad: actividad || null,
        min_cumplidas: minCumplidas ? Number(minCumplidas) : null,
        fecha_desde: fechaDesde || null,
        fecha_hasta: fechaHasta || null,
        ...overrides,
      })
    }, DEBOUNCE_MS)
  }

  function handleClear() {
    if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    setBusqueda('')
    setComision('')
    setRegional('')
    setActividad('')
    setMinCumplidas('')
    setFechaDesde('')
    setFechaHasta('')
    onClear()
  }

  useEffect(() => {
    return () => { if (debounceRef.current !== null) clearTimeout(debounceRef.current) }
  }, [])

  return (
    <div data-testid="monitor-filters" className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Búsqueda alumno"
          value={busqueda}
          onChange={(e) => { setBusqueda(e.target.value); fire({ busqueda: e.target.value || null }) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Comisión"
          value={comision}
          onChange={(e) => { setComision(e.target.value); fire({ comision: e.target.value || null }) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Regional"
          value={regional}
          onChange={(e) => { setRegional(e.target.value); fire({ regional: e.target.value || null }) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Actividad"
          value={actividad}
          onChange={(e) => { setActividad(e.target.value); fire({ actividad: e.target.value || null }) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Mín. cumplidas"
          value={minCumplidas}
          onChange={(e) => { setMinCumplidas(e.target.value); fire({ min_cumplidas: e.target.value ? Number(e.target.value) : null }) }}
          className="w-32 rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="datetime-local"
          value={fechaDesde}
          title="Fecha desde"
          onChange={(e) => { setFechaDesde(e.target.value); fire({ fecha_desde: e.target.value || null }) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="datetime-local"
          value={fechaHasta}
          title="Fecha hasta"
          onChange={(e) => { setFechaHasta(e.target.value); fire({ fecha_hasta: e.target.value || null }) }}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div>
        <Button variant="secondary" size="sm" onClick={handleClear}>
          Limpiar filtros
        </Button>
      </div>
    </div>
  )
}
