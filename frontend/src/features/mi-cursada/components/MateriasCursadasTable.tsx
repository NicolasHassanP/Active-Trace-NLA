/**
 * MateriasCursadasTable — tabla de materias cursadas con avance y detalle.
 * Task 6.2: TableWrapper + StatusBadge por estado_entrega.
 */
import { TableWrapper } from '@/shared/components/ui/TableWrapper'
import { StatusBadge } from '@/shared/components/ui/StatusBadge'
import type { MateriaCursadaRead } from '../types'

interface MateriasCursadasTableProps {
  materias: MateriaCursadaRead[]
}

const ESTADO_BADGE_MAP: Record<string, string> = {
  aprobada: 'aprobada',
  con_nota: 'pendiente',
  sin_entrega: 'sin_datos',
}

const ESTADO_LABEL_MAP: Record<string, string> = {
  aprobada: 'Aprobada',
  con_nota: 'Con nota',
  sin_entrega: 'Sin entrega',
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-[#eef0ff] rounded-full h-[6px] overflow-hidden">
        <div
          className="h-full bg-ind rounded-full"
          style={{ width: `${pct}%` }}
          aria-label={`${pct}%`}
        />
      </div>
      <span className="text-[12px] font-bold text-ink tabular-nums w-[32px] text-right">{pct}%</span>
    </div>
  )
}

export function MateriasCursadasTable({ materias }: MateriasCursadasTableProps) {
  return (
    <div className="space-y-6">
      {materias.map((materia) => (
        <div key={materia.materia_id} className="bg-white border border-line rounded-card shadow-card overflow-hidden">
          <div className="px-5 py-4 border-b border-line flex items-center justify-between gap-4">
            <div>
              <p className="text-[14px] font-bold text-ink">{materia.materia_nombre}</p>
              <p className="text-[12px] text-mut mt-[2px]">
                {materia.aprobadas} de {materia.total_actividades} aprobadas
              </p>
            </div>
            <div className="w-[140px] shrink-0">
              <ProgressBar pct={materia.avance_pct} />
            </div>
          </div>

          {materia.calificaciones.length > 0 ? (
            <TableWrapper>
              <thead>
                <tr>
                  <th className="text-left">Actividad</th>
                  <th className="text-right">Nota</th>
                  <th className="text-center">Estado</th>
                </tr>
              </thead>
              <tbody>
                {materia.calificaciones.map((cal, i) => (
                  <tr key={`${materia.materia_id}-${i}`}>
                    <td className="text-[13px] text-ink">{cal.actividad}</td>
                    <td className="text-right num">
                      {cal.nota_numerica ?? cal.nota_textual ?? '—'}
                    </td>
                    <td className="text-center">
                      <StatusBadge
                        status={ESTADO_BADGE_MAP[cal.estado_entrega] ?? 'sin_datos'}
                        label={ESTADO_LABEL_MAP[cal.estado_entrega] ?? cal.estado_entrega}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          ) : (
            <p className="text-[12.5px] text-faint px-5 py-4">Sin actividades registradas.</p>
          )}
        </div>
      ))}
    </div>
  )
}
