/**
 * MonitorToolbar — actions toolbar for the Monitor page.
 * Provides "limpiar filtros" and "exportar CSV" actions.
 * Export calls the existing client-side CSV export in monitoresService
 * then triggers the download via the shared downloadFile helper.
 * Task 4.5. < 200 LOC.
 */
import { exportarMonitorCsv } from '../services/monitoresService'
import { downloadFile } from '@/shared/services/downloadFile'
import type { MonitorFila } from '../types'

interface Props {
  filas: MonitorFila[]
  onClear: () => void
  exporting?: boolean
}

export default function MonitorToolbar({ filas, onClear, exporting = false }: Props) {
  function handleExport() {
    const blob = exportarMonitorCsv(filas)
    downloadFile(blob, 'monitor.csv')
  }

  return (
    <div data-testid="monitor-toolbar" className="flex items-center gap-3">
      <button
        onClick={onClear}
        className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
      >
        Limpiar filtros
      </button>
      <button
        onClick={handleExport}
        disabled={exporting || filas.length === 0}
        className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {exporting ? 'Exportando…' : 'Exportar CSV'}
      </button>
    </div>
  )
}
