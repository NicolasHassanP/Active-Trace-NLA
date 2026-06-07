/**
 * ComunicacionesPage — composes ComposeComunicacion + LoteStatusBandeja + AprobacionPanel.
 * Preloads destinatarios from URL search params (passed from AtrasadosPage).
 * Reads destinatarios emails + materia_id + cohorte_id from query string.
 *
 * C-27: Adds "Componer" | "Historial" tabs.
 * - Default tab: "Componer" (preserves existing behavior).
 * - "Historial" tab mounts ComunicacionesHistorial.
 * - Tab state is local (no URL change) — D5 from design.md.
 */
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ComposeComunicacion from '../components/ComposeComunicacion'
import LoteStatusBandeja from '../components/LoteStatusBandeja'
import AprobacionPanel from '../components/AprobacionPanel'
import ComunicacionesHistorial from '../components/ComunicacionesHistorial'
import { useLoteStatus } from '../hooks/comunicacionHooks'
import type { AlumnoAtrasado } from '@/features/atrasados/types'
import { PageHeader } from '@/shared/components/ui'

type ActiveTab = 'componer' | 'historial'

/** Build minimal AlumnoAtrasado stubs from email list for the compose form */
function buildDestinatariosFromEmails(emails: string[]): AlumnoAtrasado[] {
  return emails.map((email, i) => ({
    alumno_id: `dest-${i}`,
    nombre: email.split('@')[0],
    apellidos: '',
    email,
    actividades_faltantes: [],
    actividades_no_aprobadas: [],
    estado: 'atrasado' as const,
  }))
}

function AprobacionWrapper({ loteId }: { loteId: string }) {
  const { data } = useLoteStatus(loteId)
  if (!data) return null
  return <AprobacionPanel loteId={loteId} mensajes={data.mensajes} />
}

export default function ComunicacionesPage() {
  const [searchParams] = useSearchParams()
  const emailsParam = searchParams.get('destinatarios') ?? ''
  const emails = emailsParam ? emailsParam.split(',').filter(Boolean) : []
  const destinatarios = buildDestinatariosFromEmails(emails)

  const [loteId, setLoteId] = useState<string | null>(null)
  // C-27 — Tab state: default "componer" (preserves existing behavior)
  const [activeTab, setActiveTab] = useState<ActiveTab>('componer')

  return (
    <div className="space-y-8">
      <PageHeader
        title="Comunicaciones"
        subtitle={
          activeTab === 'componer' && destinatarios.length > 0
            ? `${destinatarios.length} destinatario(s) preseleccionado(s) desde alumnos atrasados.`
            : undefined
        }
      />

      {/* C-27 — Tab bar */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6" aria-label="Tabs de comunicaciones">
          <button
            data-testid="tab-componer"
            onClick={() => setActiveTab('componer')}
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === 'componer'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Componer
          </button>
          <button
            data-testid="tab-historial"
            onClick={() => setActiveTab('historial')}
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === 'historial'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Historial
          </button>
        </nav>
      </div>

      {/* C-27 — Tab: Componer (preserves existing behavior) */}
      {activeTab === 'componer' && (
        <>
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-700">Componer mensaje</h2>
            <ComposeComunicacion
              destinatarios={destinatarios}
              onEncolado={(id) => setLoteId(id)}
            />
          </section>

          {loteId && (
            <>
              <section className="space-y-4 border-t pt-6">
                <h2 className="text-lg font-semibold text-gray-700">Estado del lote</h2>
                <LoteStatusBandeja loteId={loteId} />
              </section>

              <section className="space-y-4 border-t pt-6">
                <h2 className="text-lg font-semibold text-gray-700">Aprobación</h2>
                <AprobacionWrapper loteId={loteId} />
              </section>
            </>
          )}
        </>
      )}

      {/* C-27 — Tab: Historial */}
      {activeTab === 'historial' && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-700">Mis envíos</h2>
          <ComunicacionesHistorial />
        </section>
      )}
    </div>
  )
}
