/**
 * LoteStatusBandeja — shows batch status counters and per-message detail.
 * Polling is controlled by useLoteStatus (bounded by terminal states). < 200 LOC.
 */
import { useLoteStatus } from '../hooks/comunicacionHooks'
import { StatusBadge } from '@/shared/components/ui'

interface Props {
  loteId: string
}

export default function LoteStatusBandeja({ loteId }: Props) {
  const { data, isLoading, isTerminal } = useLoteStatus(loteId)

  if (isLoading) {
    return <div className="animate-pulse h-20 bg-gray-100 rounded" />
  }

  if (!data) return null

  return (
    <div className="space-y-4" data-testid="lote-bandeja">
      {/* Counters */}
      <div className="grid grid-cols-4 gap-3">
        <Stat label="Pendientes" value={data.pendientes} color="text-yellow-700" />
        <Stat label="Enviados" value={data.enviados} color="text-green-700" />
        <Stat label="Fallidos" value={data.fallidos} color="text-red-700" />
        <Stat label="Cancelados" value={data.cancelados} color="text-gray-500" />
      </div>

      {isTerminal && (
        <p className="text-sm text-gray-500 italic" data-testid="lote-terminal">
          Todos los mensajes han alcanzado su estado final.
        </p>
      )}

      {/* Per-message detail */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs border">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-2 py-1 text-left text-gray-600">Destinatario</th>
              <th className="px-2 py-1 text-left text-gray-600">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.mensajes.map((msg) => (
              <tr key={msg.id} className="border-t">
                <td className="px-2 py-1">{msg.destinatario_email}</td>
                <td className="px-2 py-1">
                  <StatusBadge status={msg.estado} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-3 border rounded text-center">
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  )
}
