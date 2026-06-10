/**
 * PendientesAprobacionPanel — shows all Pendiente communications across the tenant.
 * Visible only to COORDINADOR / ADMIN (comunicacion:aprobar permission).
 * Allows COORDINADOR/ADMIN to approve or cancel entire lotes.
 * < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { usePendientesAprobacion, useAprobarLote, useCancelarLote } from '../hooks/comunicacionHooks'
import type { DomainError } from '@/shared/services/domainError'
import type { PendienteAprobacionItem } from '../types'
import { Button, StatusBadge } from '@/shared/components/ui'

/** Groups enriched items by lote_id */
function groupByLote(items: PendienteAprobacionItem[]): Map<string, PendienteAprobacionItem[]> {
  const map = new Map<string, PendienteAprobacionItem[]>()
  for (const item of items) {
    const bucket = map.get(item.lote_id) ?? []
    bucket.push(item)
    map.set(item.lote_id, bucket)
  }
  return map
}

interface LoteRowProps {
  loteId: string
  mensajes: PendienteAprobacionItem[]
}

function LoteRow({ loteId, mensajes }: LoteRowProps) {
  const aprobarLote = useAprobarLote()
  const cancelarLote = useCancelarLote()
  const [dismissed, setDismissed] = useState(false)

  // Optimistically hide the row as soon as the user acts
  if (dismissed) return null

  const oldest = mensajes[mensajes.length - 1]
  const senderLabel =
    oldest?.enviado_por_nombre ??
    (oldest?.enviado_por ? oldest.enviado_por.slice(0, 8) + '…' : '—')
  const asuntoLabel = oldest?.asunto_preview ?? '—'

  function handleAprobar() {
    setDismissed(true)
    aprobarLote.mutate(loteId, {
      onSuccess: () => toast.success('Lote aprobado'),
      onError: (err) => {
        setDismissed(false)
        const de = err as unknown as DomainError
        toast.error(de.detail ?? 'Error al aprobar el lote')
      },
    })
  }

  function handleCancelar() {
    setDismissed(true)
    cancelarLote.mutate(loteId, {
      onSuccess: () => toast.success('Lote cancelado'),
      onError: (err) => {
        setDismissed(false)
        const de = err as unknown as DomainError
        if (de.status === 409) {
          toast.error('Transición inválida: algunos mensajes no son cancelables')
        } else {
          toast.error(de.detail ?? 'Error al cancelar')
        }
      },
    })
  }

  return (
    <tr className="border-t hover:bg-gray-50" data-testid={`lote-row-${loteId}`}>
      <td className="px-3 py-2 font-mono text-xs text-gray-500">
        {loteId.slice(0, 8)}…
      </td>
      <td className="px-3 py-2 text-xs text-gray-600">{senderLabel}</td>
      <td className="px-3 py-2 text-xs text-gray-700 max-w-[180px] truncate" title={oldest?.asunto ?? undefined}>
        {asuntoLabel}
      </td>
      <td className="px-3 py-2 text-xs">{mensajes.length}</td>
      <td className="px-3 py-2 text-xs">
        <StatusBadge status="Pendiente" />
      </td>
      <td className="px-3 py-2 text-xs text-gray-400">
        {oldest?.creado_en ? new Date(oldest.creado_en).toLocaleString('es-AR') : '—'}
      </td>
      <td className="px-3 py-2">
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={handleAprobar}
            isLoading={aprobarLote.isPending}
            data-testid={`aprobar-lote-${loteId}`}
          >
            Aprobar lote
          </Button>
          <Button
            size="sm"
            variant="danger"
            onClick={handleCancelar}
            isLoading={cancelarLote.isPending}
            data-testid={`cancelar-lote-${loteId}`}
          >
            Cancelar
          </Button>
        </div>
      </td>
    </tr>
  )
}

export default function PendientesAprobacionPanel() {
  const { data, isLoading, isError } = usePendientesAprobacion()

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando pendientes…</p>
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600" data-testid="pendientes-error">
        Error al cargar las comunicaciones pendientes.
      </p>
    )
  }

  const items = data?.items ?? []

  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500" data-testid="pendientes-empty">
        No hay comunicaciones pendientes de aprobación.
      </p>
    )
  }

  const loteMap = groupByLote(items)

  return (
    <div className="overflow-x-auto" data-testid="pendientes-aprobacion-panel">
      <p className="mb-2 text-xs text-gray-500">
        {data?.total ?? items.length} mensaje(s) pendiente(s) en {loteMap.size} lote(s).
      </p>
      <table className="min-w-full text-sm border rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Lote</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Remitente</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Asunto</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Mensajes</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Estado</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Fecha</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(loteMap.entries()).map(([loteId, mensajes]) => (
            <LoteRow key={loteId} loteId={loteId} mensajes={mensajes} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
