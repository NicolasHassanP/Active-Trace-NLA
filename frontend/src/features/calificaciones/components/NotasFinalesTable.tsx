/**
 * NotasFinalesTable — final grades per student (F2.5) with CSV export and sortable columns.
 * < 200 LOC.
 */
import { useState, useMemo } from 'react'
import { useNotasFinales } from '../hooks/calificacionesHooks'
import type { DomainError } from '@/shared/services/domainError'
import type { NotaFinalAlumno } from '../types'
import { Button } from '@/shared/components/ui'

type SortKey = 'nombre' | 'nota_final' | 'actividades_consideradas'
type SortDir = 'asc' | 'desc'

interface Props {
  materia_id: string
  actividades?: string[]
}

function exportCsv(data: NotaFinalAlumno[]) {
  const header = 'alumno,nota_final,actividades_consideradas\n'
  const rows = data
    .map((r) => {
      const nombre = r.nombre && r.apellidos ? `${r.apellidos}, ${r.nombre}` : r.entrada_padron_id
      return `${nombre},${r.nota_final ?? ''},${r.actividades_consideradas}`
    })
    .join('\n')
  const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'notas_finales.csv'
  link.click()
  URL.revokeObjectURL(url)
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="ml-1 text-gray-300">↕</span>
  return <span className="ml-1">{dir === 'asc' ? '↑' : '↓'}</span>
}

export default function NotasFinalesTable({ materia_id, actividades = [] }: Props) {
  const { data, isLoading, isError, error } = useNotasFinales(materia_id, actividades)
  const [sortKey, setSortKey] = useState<SortKey>('nota_final')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const sorted = useMemo(() => {
    if (!data) return []
    return [...data].sort((a, b) => {
      let valA: string | number
      let valB: string | number
      if (sortKey === 'nombre') {
        valA = a.apellidos ?? ''
        valB = b.apellidos ?? ''
        return sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA)
      } else if (sortKey === 'nota_final') {
        valA = a.nota_final ?? -1
        valB = b.nota_final ?? -1
      } else {
        valA = a.actividades_consideradas
        valB = b.actividades_consideradas
      }
      return sortDir === 'asc' ? (valA as number) - (valB as number) : (valB as number) - (valA as number)
    })
  }, [data, sortKey, sortDir])

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  if (isLoading) return <p className="text-sm text-gray-500">Cargando notas finales…</p>
  if (isError) {
    const de = error as unknown as DomainError
    return <p role="alert" className="text-sm text-red-600">{de.detail ?? 'Error al cargar las notas finales'}</p>
  }
  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-500 italic">No hay datos de notas finales para esta materia.</p>
  }

  const thClass = 'px-4 py-2 font-medium text-gray-600 cursor-pointer select-none hover:text-indigo-600'

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={() => exportCsv(sorted)} data-testid="export-notas-csv">
          Exportar CSV
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border rounded">
          <thead className="bg-gray-50">
            <tr>
              <th className={`${thClass} text-left`} onClick={() => handleSort('nombre')}>
                Alumno <SortIcon active={sortKey === 'nombre'} dir={sortDir} />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('nota_final')}>
                Nota final <SortIcon active={sortKey === 'nota_final'} dir={sortDir} />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('actividades_consideradas')}>
                Actividades consideradas <SortIcon active={sortKey === 'actividades_consideradas'} dir={sortDir} />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.entrada_padron_id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 text-gray-700">
                  {row.nombre && row.apellidos ? `${row.apellidos}, ${row.nombre}` : row.entrada_padron_id}
                </td>
                <td className="px-4 py-2 text-right font-semibold">
                  {row.nota_final != null ? Number(row.nota_final).toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2 text-right text-gray-500">
                  {row.actividades_consideradas}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-gray-400">{sorted.length} alumno(s)</p>
      </div>
    </div>
  )
}
