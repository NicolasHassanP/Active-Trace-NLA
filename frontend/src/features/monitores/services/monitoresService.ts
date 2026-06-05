/**
 * monitoresService — wraps GET /api/v1/analisis/monitor and client-side CSV export.
 *
 * OQ-3 RESOLVED: Monitor export is client-side.
 * The backend returns a flat List[MonitorFila] — we build the CSV string in
 * the browser and use the shared downloadFile helper to trigger the download.
 * No backend export endpoint needed.
 *
 * Tasks 4.2, 4.3.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { MonitorFila, MonitorParams } from '../types'

// ---------------------------------------------------------------------------
// Task 4.2 — listarMonitor
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/analisis/monitor
 * Returns the monitor rows for all active students in the tenant (scope: grant-based).
 * All filter values that are null/undefined are omitted from the request.
 */
export async function listarMonitor(params: MonitorParams): Promise<MonitorFila[]> {
  try {
    const query: Record<string, string | number | string[]> = {}

    if (params.materia_id != null) query['materia_id'] = params.materia_id
    if (params.cohorte_id != null) query['cohorte_id'] = params.cohorte_id
    if (params.comision != null) query['comision'] = params.comision
    if (params.regional != null) query['regional'] = params.regional
    if (params.busqueda != null) query['busqueda'] = params.busqueda
    if (params.actividad != null) query['actividad'] = params.actividad
    if (params.min_cumplidas != null) query['min_cumplidas'] = params.min_cumplidas
    if (params.fecha_desde != null) query['fecha_desde'] = params.fecha_desde
    if (params.fecha_hasta != null) query['fecha_hasta'] = params.fecha_hasta
    if (params.actividades && params.actividades.length > 0) {
      query['actividades'] = params.actividades
    }

    const response = await apiClient.get<MonitorFila[]>('/analisis/monitor', { params: query })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 4.3 — exportarMonitorCsv (client-side, OQ-3 resolved)
// ---------------------------------------------------------------------------

/**
 * Builds a CSV Blob from the already-fetched MonitorFila rows.
 * Columns: entrada_padron_id, estado, aprobadas, faltantes.
 *
 * Caller should use downloadFile() from @/shared/services/downloadFile
 * to trigger the browser download. No HTTP request made here.
 */
export function exportarMonitorCsv(filas: MonitorFila[]): Blob {
  const header = 'entrada_padron_id,estado,aprobadas,faltantes'
  const rows = filas.map(
    (f) =>
      `${f.entrada_padron_id},${f.estado},${f.aprobadas},${f.faltantes}`,
  )
  const csv = [header, ...rows].join('\n')
  return new Blob([csv], { type: 'text/csv' })
}
