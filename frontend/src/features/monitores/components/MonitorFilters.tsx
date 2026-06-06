/**
 * MonitorFilters — full filter bar for the monitor page.
 * Task 4.5. < 200 LOC.
 */
import { useState } from 'react'
import type { MonitorParams } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  onFilter: (params: MonitorParams) => void
  onClear: () => void
}

export default function MonitorFilters({ onFilter, onClear }: Props) {
  const [materiaId, setMateriaId] = useState('')
  const [cohorteId, setCohorteId] = useState('')
  const [comision, setComision] = useState('')
  const [regional, setRegional] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [actividad, setActividad] = useState('')
  const [minCumplidas, setMinCumplidas] = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  function handleApply() {
    onFilter({
      materia_id: materiaId || null,
      cohorte_id: cohorteId || null,
      comision: comision || null,
      regional: regional || null,
      busqueda: busqueda || null,
      actividad: actividad || null,
      min_cumplidas: minCumplidas ? Number(minCumplidas) : null,
      fecha_desde: fechaDesde || null,
      fecha_hasta: fechaHasta || null,
    })
  }

  function handleClear() {
    setMateriaId('')
    setCohorteId('')
    setComision('')
    setRegional('')
    setBusqueda('')
    setActividad('')
    setMinCumplidas('')
    setFechaDesde('')
    setFechaHasta('')
    onClear()
  }

  return (
    <div data-testid="monitor-filters" className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="ID materia"
          value={materiaId}
          onChange={(e) => setMateriaId(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="ID cohorte"
          value={cohorteId}
          onChange={(e) => setCohorteId(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Comisión"
          value={comision}
          onChange={(e) => setComision(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Regional"
          value={regional}
          onChange={(e) => setRegional(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Búsqueda alumno"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Actividad"
          value={actividad}
          onChange={(e) => setActividad(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Mín. cumplidas"
          value={minCumplidas}
          onChange={(e) => setMinCumplidas(e.target.value)}
          className="w-32 rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="datetime-local"
          value={fechaDesde}
          onChange={(e) => setFechaDesde(e.target.value)}
          title="Fecha desde"
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
        <input
          type="datetime-local"
          value={fechaHasta}
          onChange={(e) => setFechaHasta(e.target.value)}
          title="Fecha hasta"
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={handleApply}>
          Filtrar
        </Button>
        <Button variant="secondary" size="sm" onClick={handleClear}>
          Limpiar filtros
        </Button>
      </div>
    </div>
  )
}
