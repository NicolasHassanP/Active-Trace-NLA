/**
 * SeguimientoFiltros — filter panel for the Seguimiento page.
 *
 * UX rules:
 *  - Búsqueda libre: debounce 300ms before calling onFilter
 *  - Comisión, Regional, Mín. cumplidas: fire onChange immediately
 *  - No explicit "Filtrar" submit button — filters are reactive
 *
 * < 200 LOC. No `any`. Only Tailwind.
 */
import { useEffect, useRef, useState } from 'react'
import type { SeguimientoParams } from '../types'
import { Button } from '@/shared/components/ui'

interface Props {
  onFilter: (params: SeguimientoParams) => void
  onClear: () => void
}

const DEBOUNCE_MS = 300

export default function SeguimientoFiltros({ onFilter, onClear }: Props) {
  const [busqueda, setBusqueda] = useState('')
  const [comision, setComision] = useState('')
  const [regional, setRegional] = useState('')
  const [minCumplidas, setMinCumplidas] = useState('')

  // Debounce ref for búsqueda
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Derived params — used by immediate-fire controls
  function buildParams(overrides: Partial<SeguimientoParams> = {}): SeguimientoParams {
    return {
      busqueda: busqueda || null,
      comision: comision || null,
      regional: regional || null,
      min_cumplidas: minCumplidas ? Number(minCumplidas) : null,
      ...overrides,
    }
  }

  // Búsqueda libre — debounced
  function handleBusquedaChange(value: string) {
    setBusqueda(value)
    if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      onFilter(buildParams({ busqueda: value || null }))
    }, DEBOUNCE_MS)
  }

  // Immediate-fire handlers
  function handleComisionChange(value: string) {
    setComision(value)
    onFilter(buildParams({ comision: value || null }))
  }

  function handleRegionalChange(value: string) {
    setRegional(value)
    onFilter(buildParams({ regional: value || null }))
  }

  function handleMinCumplidasChange(value: string) {
    setMinCumplidas(value)
    onFilter(buildParams({ min_cumplidas: value ? Number(value) : null }))
  }

  function handleClear() {
    if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    setBusqueda('')
    setComision('')
    setRegional('')
    setMinCumplidas('')
    onClear()
  }

  // Clean up debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    }
  }, [])

  return (
    <div data-testid="seguimiento-filtros" className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Buscar alumno o email"
          value={busqueda}
          onChange={(e) => handleBusquedaChange(e.target.value)}
          className="min-w-[200px] rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          aria-label="Búsqueda libre"
        />
        <input
          type="text"
          placeholder="Comisión"
          value={comision}
          onChange={(e) => handleComisionChange(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          aria-label="Comisión"
        />
        <input
          type="text"
          placeholder="Regional"
          value={regional}
          onChange={(e) => handleRegionalChange(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          aria-label="Regional"
        />
        <input
          type="number"
          placeholder="Mín. cumplidas"
          min={0}
          value={minCumplidas}
          onChange={(e) => handleMinCumplidasChange(e.target.value)}
          className="w-36 rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          aria-label="Mínimo de actividades cumplidas"
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
