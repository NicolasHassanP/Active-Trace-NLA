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
import type { MonitorFila, MonitorParams, MateriaItem, CohorteItem, CarreraItem } from '../types'

// ---------------------------------------------------------------------------
// Global-scope: all tenant materias (ADMIN / COORDINADOR only)
// ---------------------------------------------------------------------------

export async function listarTodasMaterias(): Promise<MateriaItem[]> {
  try {
    const response = await apiClient.get<MateriaItem[]>('/admin/materias')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

export async function listarTodosCohortes(): Promise<CohorteItem[]> {
  try {
    const response = await apiClient.get<CohorteItem[]>('/admin/cohortes')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

export async function listarTodasCarreras(): Promise<CarreraItem[]> {
  try {
    const response = await apiClient.get<CarreraItem[]>('/admin/carreras')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

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
 * Escapes a CSV cell value: wraps in double-quotes if the value contains
 * a comma, double-quote, or newline, and escapes inner double-quotes.
 */
function escapeCsvCell(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * Builds a CSV Blob from the already-fetched MonitorFila rows.
 * Columns: nombre, apellidos, email, comision, regional, estado, aprobadas, faltantes.
 * Includes an extra `actividades_aprobadas` column with a semicolon-joined list
 * of approved activity names (from actividades_detalle).
 *
 * Caller should use downloadFile() from @/shared/services/downloadFile
 * to trigger the browser download. No HTTP request made here.
 */
export function exportarMonitorCsv(filas: MonitorFila[]): Blob {
  const header =
    'nombre,apellidos,email,comision,regional,estado,aprobadas,faltantes,actividades_aprobadas'

  const rows = filas.map((f) => {
    const aprobadas = f.actividades_detalle
      .filter((a) => a.aprobado)
      .map((a) => a.actividad)
      .join('; ')

    return [
      escapeCsvCell(f.nombre ?? ''),
      escapeCsvCell(f.apellidos ?? ''),
      escapeCsvCell(f.email ?? ''),
      escapeCsvCell(f.comision ?? ''),
      escapeCsvCell(f.regional ?? ''),
      escapeCsvCell(f.estado),
      String(f.aprobadas),
      String(f.faltantes),
      escapeCsvCell(aprobadas),
    ].join(',')
  })

  const csv = [header, ...rows].join('\n')
  return new Blob([csv], { type: 'text/csv' })
}
