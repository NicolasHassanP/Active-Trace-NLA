/**
 * MisColoquiosPage — HU-47 ALUMNO.
 * Lista convocatorias donde el alumno es candidato (no cerradas).
 * Por cada convocatoria muestra turnos con cupos disponibles.
 * Botón "Reservar" o "Cancelar reserva" según estado.
 * Identidad siempre del JWT — no se pasa user_id como prop.
 * < 200 LOC.
 */
import { PageHeader } from '@/shared/components/ui/PageHeader'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { Button } from '@/shared/components/ui/Button'
import { useMisConvocatorias, useReservarTurno, useCancelarReserva } from '../hooks/misColoquiosHooks'
import type { ConvocatoriasAlumnoRead, TurnoConCupoRead } from '../types'

function formatFecha(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}

interface TurnoRowProps {
  turno: TurnoConCupoRead
  convocatoria: ConvocatoriasAlumnoRead
  onReservar: (turnoId: string, evaluacionId: string) => void
  onCancelar: (reservaId: string) => void
  isLoadingReservar: boolean
  isLoadingCancelar: boolean
}

function TurnoRow({
  turno,
  convocatoria,
  onReservar,
  onCancelar,
  isLoadingReservar,
  isLoadingCancelar,
}: TurnoRowProps) {
  const tieneReservaActiva = convocatoria.reserva_activa_id !== null
  const sinCupo = turno.cupos_disponibles === 0

  return (
    <div className="flex items-center justify-between py-2 border-b border-line last:border-0">
      <div className="space-y-0.5">
        <p className="text-[13px] font-semibold text-ink">
          {formatFecha(turno.fecha)}
          {turno.franja ? ` · ${turno.franja}` : ''}
        </p>
        <p className="text-[12px] text-mut">
          {sinCupo ? 'Sin cupos' : `${turno.cupos_disponibles} cupos disponibles`}
        </p>
      </div>

      {tieneReservaActiva ? (
        <Button
          variant="danger"
          size="sm"
          isLoading={isLoadingCancelar}
          onClick={() => onCancelar(convocatoria.reserva_activa_id!)}
        >
          Cancelar reserva
        </Button>
      ) : (
        <Button
          variant="primary"
          size="sm"
          disabled={sinCupo}
          isLoading={isLoadingReservar}
          onClick={() => onReservar(turno.id, convocatoria.evaluacion_id)}
        >
          Reservar
        </Button>
      )}
    </div>
  )
}

interface ConvocatoriaCardProps {
  convocatoria: ConvocatoriasAlumnoRead
  onReservar: (turnoId: string, evaluacionId: string) => void
  onCancelar: (reservaId: string) => void
  isLoadingReservar: boolean
  isLoadingCancelar: boolean
}

function ConvocatoriaCard({
  convocatoria,
  onReservar,
  onCancelar,
  isLoadingReservar,
  isLoadingCancelar,
}: ConvocatoriaCardProps) {
  return (
    <div className="bg-white border border-line rounded-card shadow-card p-4 space-y-3">
      <div>
        <p className="text-[14px] font-bold text-ink">{convocatoria.materia_nombre}</p>
        <p className="text-[12px] text-mut">
          {convocatoria.tipo} · Instancia {convocatoria.instancia}
        </p>
      </div>

      {convocatoria.turnos.length === 0 ? (
        <p className="text-[12px] text-mut">Sin turnos disponibles.</p>
      ) : (
        <div>
          {convocatoria.turnos.map((turno) => (
            <TurnoRow
              key={turno.id}
              turno={turno}
              convocatoria={convocatoria}
              onReservar={onReservar}
              onCancelar={onCancelar}
              isLoadingReservar={isLoadingReservar}
              isLoadingCancelar={isLoadingCancelar}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function MisColoquiosPage() {
  const { data: convocatorias, isLoading, isError } = useMisConvocatorias()
  const reservarMutation = useReservarTurno()
  const cancelarMutation = useCancelarReserva()

  function handleReservar(turnoId: string, evaluacionId: string) {
    reservarMutation.mutate({ turno_id: turnoId, evaluacion_id: evaluacionId })
  }

  function handleCancelar(reservaId: string) {
    cancelarMutation.mutate(reservaId)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mis coloquios"
        subtitle="Convocatorias disponibles donde sos candidato. Reservá o cancelá tus turnos."
      />

      {isLoading && (
        <p className="text-[13px] text-mut py-4">Cargando convocatorias…</p>
      )}

      {isError && (
        <EmptyState
          title="No se pudieron cargar las convocatorias"
          description="Intentá recargar la página. Si el problema persiste, contactá al soporte."
        />
      )}

      {convocatorias && convocatorias.length === 0 && (
        <EmptyState
          title="Sin convocatorias disponibles"
          description="No tenés convocatorias activas en este momento. El coordinador debe habilitarlas."
        />
      )}

      {convocatorias && convocatorias.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {convocatorias.map((conv) => (
            <ConvocatoriaCard
              key={conv.evaluacion_id}
              convocatoria={conv}
              onReservar={handleReservar}
              onCancelar={handleCancelar}
              isLoadingReservar={reservarMutation.isPending}
              isLoadingCancelar={cancelarMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}
