/**
 * ComunicacionesPage — composes ComposeComunicacion + LoteStatusBandeja + AprobacionPanel.
 * Preloads destinatarios from URL search params (passed from AtrasadosPage).
 * Reads destinatarios emails + materia_id + cohorte_id from query string.
 */
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ComposeComunicacion from '../components/ComposeComunicacion'
import LoteStatusBandeja from '../components/LoteStatusBandeja'
import AprobacionPanel from '../components/AprobacionPanel'
import { useLoteStatus } from '../hooks/comunicacionHooks'
import type { AlumnoAtrasado } from '@/features/atrasados/types'
import { PageHeader } from '@/shared/components/ui'

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

  return (
    <div className="space-y-8">
      <PageHeader
        title="Comunicaciones"
        subtitle={destinatarios.length > 0 ? `${destinatarios.length} destinatario(s) preseleccionado(s) desde alumnos atrasados.` : undefined}
      />

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
    </div>
  )
}
