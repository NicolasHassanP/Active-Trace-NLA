/**
 * ComunicacionesHistorial — tabla de historial de envíos propios del usuario (C-27).
 *
 * Consume GET /comunicaciones/mis-envios via useMisEnvios.
 * Ofrece filtro por estado y paginación Anterior/Siguiente.
 * Maneja estados: carga (spinner), error, vacío, y tabla de datos.
 *
 * No contiene lógica de negocio — solo presentación.
 * Design decision D5: tab historial, estado local para filtro/página.
 */
import { useState } from 'react'
import { useMisEnvios } from '../hooks/comunicacionHooks'
import type { EstadoComunicacion } from '../types'

const PAGE_SIZE = 20

/** Estado badge colors — matches the comunicacion state machine */
const ESTADO_BADGE: Record<string, string> = {
  Pendiente: 'bg-yellow-100 text-yellow-800',
  Enviando: 'bg-blue-100 text-blue-800',
  Enviado: 'bg-green-100 text-green-800',
  Error: 'bg-red-100 text-red-800',
  Cancelado: 'bg-gray-100 text-gray-700',
}

// Note: backend uses 'Error' but frontend type uses 'Fallido' — pre-existing mismatch.
// Using string to accommodate both until the type is reconciled.
const ESTADOS_FILTRO: Array<{ label: string; value: string }> = [
  { label: 'Todos', value: '' },
  { label: 'Pendiente', value: 'Pendiente' },
  { label: 'Enviando', value: 'Enviando' },
  { label: 'Enviado', value: 'Enviado' },
  { label: 'Error', value: 'Error' },
  { label: 'Cancelado', value: 'Cancelado' },
]

function formatFecha(isoString: string): string {
  if (!isoString) return '—'
  try {
    return new Date(isoString).toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}

export default function ComunicacionesHistorial() {
  const [estadoFiltro, setEstadoFiltro] = useState<string>('')
  const [offset, setOffset] = useState(0)

  const params = {
    ...(estadoFiltro ? { estado: estadoFiltro as EstadoComunicacion } : {}),
    offset,
    limit: PAGE_SIZE,
  }

  const { data, isLoading, isError, error } = useMisEnvios(params)

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + PAGE_SIZE < total

  function handleEstadoChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setEstadoFiltro(e.target.value)
    setOffset(0)  // reset pagination on filter change
  }

  function handlePrev() {
    setOffset((prev) => Math.max(0, prev - PAGE_SIZE))
  }

  function handleNext() {
    if (hasNext) setOffset((prev) => prev + PAGE_SIZE)
  }

  return (
    <div data-testid="historial-panel" className="space-y-4">
      {/* Filtro de estado */}
      <div className="flex items-center gap-3">
        <label htmlFor="estado-filtro" className="text-sm font-medium text-gray-700">
          Filtrar por estado:
        </label>
        <select
          id="estado-filtro"
          data-testid="estado-filtro"
          value={estadoFiltro}
          onChange={handleEstadoChange}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {ESTADOS_FILTRO.map(({ label, value }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {total > 0 && (
          <span className="text-sm text-gray-500">
            {total} resultado{total !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Estado de carga */}
      {isLoading && (
        <div data-testid="historial-loading" className="flex items-center gap-2 py-8 text-gray-500">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <span>Cargando historial…</span>
        </div>
      )}

      {/* Estado de error */}
      {isError && !isLoading && (
        <div
          data-testid="historial-error"
          className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          No se pudo cargar el historial de envíos.
          {error instanceof Error && (
            <span className="block mt-1 text-xs text-red-500">{error.message}</span>
          )}
        </div>
      )}

      {/* Estado vacío */}
      {!isLoading && !isError && items.length === 0 && (
        <div
          data-testid="historial-vacio"
          className="rounded-lg border border-dashed border-gray-300 py-12 text-center"
        >
          <p className="text-gray-500">No tenés envíos todavía.</p>
          {estadoFiltro && (
            <p className="mt-1 text-sm text-gray-400">
              Probá cambiando el filtro de estado.
            </p>
          )}
        </div>
      )}

      {/* Tabla de historial */}
      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table data-testid="historial-tabla" className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Asunto</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Destinatario</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {items.map((com) => (
                <tr key={com.id} className="hover:bg-gray-50">
                  <td className="max-w-xs truncate px-4 py-3 text-gray-900" title={com.asunto}>
                    {com.asunto}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTADO_BADGE[com.estado] ?? 'bg-gray-100 text-gray-700'}`}
                    >
                      {com.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{com.destinatario_email}</td>
                  <td className="px-4 py-3 text-gray-500">{formatFecha(com.creado_en)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Paginación */}
      {!isLoading && !isError && total > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Mostrando {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </span>
          <div className="flex gap-2">
            <button
              data-testid="btn-anterior"
              onClick={handlePrev}
              disabled={!hasPrev}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Anterior
            </button>
            <button
              data-testid="btn-siguiente"
              onClick={handleNext}
              disabled={!hasNext}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
