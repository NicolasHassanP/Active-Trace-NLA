/**
 * AuditoriaMetricasPanel — read-only metrics panel for admin-auditoria.
 * Renders 4 metric tables/KPIs + ultimas-acciones table.
 * Actor and materia columns show resolved names (actor_nombre, materia_nombre)
 * with "(desconocido)" / "—" fallbacks. No mutations. < 200 LOC.
 */
import {
  useAccionesPorDia,
  useInteraccionesDocente,
  useInteraccionesDocenteMateria,
  useComunicacionesPorDocente,
  useUltimasAcciones,
} from '../hooks/auditoriaHooks'

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">{children}</h3>
}

function LoadingRow() {
  return <p className="text-sm text-gray-500">Cargando…</p>
}

function ErrorRow() {
  return <p className="text-sm text-red-600">No se pudo cargar.</p>
}

export default function AuditoriaMetricasPanel() {
  const accionesPorDia = useAccionesPorDia({})
  const interacciones = useInteraccionesDocente({})
  const interaccionesMat = useInteraccionesDocenteMateria({})
  const comunicaciones = useComunicacionesPorDocente()
  const ultimas = useUltimasAcciones()

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
      {/* Acciones por día */}
      <section data-testid="metricas-acciones-por-dia" className="space-y-2">
        <SectionTitle>Acciones por día</SectionTitle>
        {accionesPorDia.isLoading && <LoadingRow />}
        {accionesPorDia.isError && <ErrorRow />}
        {!accionesPorDia.isLoading && !accionesPorDia.isError && (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Día</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {(accionesPorDia.data?.items ?? []).map((item, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 font-mono text-xs text-gray-600">{item.dia.slice(0, 10)}</td>
                  <td className="px-3 py-2 text-gray-900">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Interacciones docente */}
      <section data-testid="metricas-interacciones-docente" className="space-y-2">
        <SectionTitle>Interacciones por docente</SectionTitle>
        {interacciones.isLoading && <LoadingRow />}
        {interacciones.isError && <ErrorRow />}
        {!interacciones.isLoading && !interacciones.isError && (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Actor</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Acción</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {(interacciones.data?.items ?? []).map((item, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 text-xs text-gray-700">{item.actor_nombre ?? '(desconocido)'}</td>
                  <td className="px-3 py-2 text-gray-900">{item.accion}</td>
                  <td className="px-3 py-2 text-gray-900">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Interacciones docente materia */}
      <section data-testid="metricas-interacciones-docente-materia" className="space-y-2">
        <SectionTitle>Interacciones docente × materia</SectionTitle>
        {interaccionesMat.isLoading && <LoadingRow />}
        {interaccionesMat.isError && <ErrorRow />}
        {!interaccionesMat.isLoading && !interaccionesMat.isError && (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Actor</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Materia</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {(interaccionesMat.data?.items ?? []).map((item, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 text-xs text-gray-700">{item.actor_nombre ?? '(desconocido)'}</td>
                  <td className="px-3 py-2 text-xs text-gray-700">{item.materia_nombre ?? '—'}</td>
                  <td className="px-3 py-2 text-gray-900">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Comunicaciones por docente */}
      <section data-testid="metricas-comunicaciones-por-docente" className="space-y-2">
        <SectionTitle>Comunicaciones por docente</SectionTitle>
        {comunicaciones.isLoading && <LoadingRow />}
        {comunicaciones.isError && <ErrorRow />}
        {!comunicaciones.isLoading && !comunicaciones.isError && (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Enviado por</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Estado</th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {(comunicaciones.data?.items ?? []).map((item, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 font-mono text-xs text-gray-500">
                    {item.enviado_por ? item.enviado_por.slice(0, 8) + '…' : '—'}
                  </td>
                  <td className="px-3 py-2 text-gray-900">{item.estado}</td>
                  <td className="px-3 py-2 text-gray-900">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Últimas acciones — full width */}
      <section data-testid="metricas-ultimas-acciones" className="col-span-full space-y-2">
        <SectionTitle>Últimas acciones</SectionTitle>
        {ultimas.isLoading && <LoadingRow />}
        {ultimas.isError && <ErrorRow />}
        {!ultimas.isLoading && !ultimas.isError && (
          <table className="min-w-full divide-y divide-gray-200 text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium uppercase text-gray-500">Fecha</th>
                <th className="px-3 py-2 text-left font-medium uppercase text-gray-500">Actor</th>
                <th className="px-3 py-2 text-left font-medium uppercase text-gray-500">Acción</th>
                <th className="px-3 py-2 text-left font-medium uppercase text-gray-500">Módulo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {(ultimas.data ?? []).map((e) => (
                <tr key={e.id}>
                  <td className="px-3 py-2 font-mono text-gray-600">{e.created_at.slice(0, 19).replace('T', ' ')}</td>
                  <td className="px-3 py-2 text-gray-700">{e.actor_nombre ?? '(desconocido)'}</td>
                  <td className="px-3 py-2 font-medium text-gray-900">{e.accion}</td>
                  <td className="px-3 py-2 text-gray-700">{e.modulo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
