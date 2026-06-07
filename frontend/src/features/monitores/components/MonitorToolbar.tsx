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
import { Button } from '@/shared/components/ui'

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
      <Button
        size="sm"
        onClick={handleExport}
        isLoading={exporting}
        disabled={exporting || filas.length === 0}
      >
        Exportar CSV
      </Button>
    </div>
  )
}
