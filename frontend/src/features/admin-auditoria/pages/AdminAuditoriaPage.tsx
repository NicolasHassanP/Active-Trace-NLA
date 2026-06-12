/**
 * AdminAuditoriaPage — /admin/auditoria
 * Read-only audit panel for ADMIN.
 * RBAC gate: ADMIN only (auditoria:ver). Fail-closed.
 * Tabs: Eventos (paginated list + filters) | Métricas (KPI panels + ultimas-acciones).
 * < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import Forbidden403 from '@/shared/components/Forbidden403'
import { PageHeader } from '@/shared/components/ui'
import type { Role } from '@/features/auth/types'
import type { AuditoriaFiltros } from '../types'
import { useEventosAuditoria } from '../hooks/auditoriaHooks'
import AuditoriaEventosTable from '../components/AuditoriaEventosTable'
import AuditoriaMetricasPanel from '../components/AuditoriaMetricasPanel'

const ALLOWED_ROLES: Role[] = ['ADMIN']
const DEFAULT_FILTROS: AuditoriaFiltros = { limit: 50, offset: 0 }

type TabId = 'eventos' | 'metricas'

export default function AdminAuditoriaPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))
  if (!isAllowed) return <Forbidden403 />
  return <AuditoriaContent />
}

function AuditoriaContent() {
  const [tab, setTab] = useState<TabId>('eventos')

  return (
    <div className="space-y-6" data-testid="admin-auditoria-page">
      <PageHeader
        title="Auditoría"
        subtitle="Consulta el log de eventos y las métricas del panel. Solo lectura."
      />

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6" aria-label="Vistas de auditoría">
          {([
            { id: 'eventos' as TabId, label: 'Eventos' },
            { id: 'metricas' as TabId, label: 'Métricas' },
          ]).map(({ id, label }) => (
            <button
              key={id}
              role="tab"
              type="button"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`pb-3 text-sm font-medium ${
                tab === id
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'eventos' && <EventosTab />}
      {tab === 'metricas' && <AuditoriaMetricasPanel />}
    </div>
  )
}

function EventosTab() {
  const [filtros, setFiltros] = useState<AuditoriaFiltros>(DEFAULT_FILTROS)
  const query = useEventosAuditoria(filtros)

  return (
    <section className="space-y-4">
      {query.isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          No se pudieron cargar los eventos de auditoría.
        </div>
      )}
      <AuditoriaEventosTable
        events={query.data ?? []}
        filtros={filtros}
        onFiltrosChange={setFiltros}
        isLoading={query.isLoading}
      />
    </section>
  )
}
