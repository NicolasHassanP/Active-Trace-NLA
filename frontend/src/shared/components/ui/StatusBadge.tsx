interface StatusBadgeProps {
  status: string
  label?: string
  className?: string
}

type ColorClasses = { color: string; bg: string }

const STATUS_COLOR_MAP: Record<string, ColorClasses> = {
  // verde — activo / vigente / completado / aprobado
  vigente:    { color: '#16a34a', bg: '#ecfdf3' },
  activo:     { color: '#16a34a', bg: '#ecfdf3' },
  activa:     { color: '#16a34a', bg: '#ecfdf3' },
  al_dia:     { color: '#16a34a', bg: '#ecfdf3' },
  hecha:      { color: '#16a34a', bg: '#ecfdf3' },
  pagado:     { color: '#16a34a', bg: '#ecfdf3' },
  publicado:  { color: '#16a34a', bg: '#ecfdf3' },
  aprobado:   { color: '#16a34a', bg: '#ecfdf3' },
  aprobada:   { color: '#16a34a', bg: '#ecfdf3' },
  realizado:  { color: '#16a34a', bg: '#ecfdf3' },
  realizada:  { color: '#16a34a', bg: '#ecfdf3' },

  // ámbar — pendiente / por vencer
  pendiente:   { color: '#d97706', bg: '#fef6e7' },
  por_vencer:  { color: '#d97706', bg: '#fef6e7' },
  programado:  { color: '#d97706', bg: '#fef6e7' },
  programada:  { color: '#d97706', bg: '#fef6e7' },
  futuro:      { color: '#d97706', bg: '#fef6e7' },
  futura:      { color: '#d97706', bg: '#fef6e7' },

  // rojo — atrasado / en riesgo / suspendido / cancelado
  atrasado:   { color: '#e7515a', bg: '#fff1f0' },
  vencido:    { color: '#e7515a', bg: '#fff1f0' },
  en_riesgo:  { color: '#e7515a', bg: '#fff1f0' },
  suspendido: { color: '#e7515a', bg: '#fff1f0' },
  cancelada:  { color: '#e7515a', bg: '#fff1f0' },
  cancelado:  { color: '#e7515a', bg: '#fff1f0' },
  rechazado:  { color: '#e7515a', bg: '#fff1f0' },
  rechazada:  { color: '#e7515a', bg: '#fff1f0' },
  inactivo:   { color: '#e7515a', bg: '#fff1f0' },

  // índigo — en curso / abierta
  en_curso: { color: '#4338ca', bg: '#eef0ff' },
  abierta:  { color: '#4338ca', bg: '#eef0ff' },
  abierto:  { color: '#4338ca', bg: '#eef0ff' },

  // gris — borrador / cerrada / sin datos
  borrador:  { color: '#6b7280', bg: '#f1f2f5' },
  cerrada:   { color: '#6b7280', bg: '#f1f2f5' },
  cerrado:   { color: '#6b7280', bg: '#f1f2f5' },
  sin_datos: { color: '#6b7280', bg: '#f1f2f5' },
  postergado: { color: '#6b7280', bg: '#f1f2f5' },
  postergada: { color: '#6b7280', bg: '#f1f2f5' },
}

const DEFAULT_COLOR: ColorClasses = { color: '#6b7280', bg: '#f1f2f5' }

const STATUS_LABEL_MAP: Record<string, string> = {
  vigente:    'Vigente',   activo:     'Activo',    activa:     'Activa',
  al_dia:     'Al día',    hecha:      'Hecha',     pagado:     'Pagado',
  publicado:  'Publicado', aprobado:   'Aprobado',  aprobada:   'Aprobada',
  realizado:  'Realizado', realizada:  'Realizada',
  pendiente:  'Pendiente', por_vencer: 'Por vencer',
  programado: 'Programado',programada: 'Programada',futuro:     'Futuro',
  futura:     'Futura',
  atrasado:   'Atrasado',  vencido:    'Vencido',   en_riesgo:  'En riesgo',
  suspendido: 'Suspendido',cancelada:  'Cancelada', cancelado:  'Cancelado',
  rechazado:  'Rechazado', rechazada:  'Rechazada', inactivo:   'Inactivo',
  en_curso:   'En curso',  abierta:    'Abierta',   abierto:    'Abierto',
  borrador:   'Borrador',  cerrada:    'Cerrada',   cerrado:    'Cerrado',
  sin_datos:  'Sin datos', postergado: 'Postergado',postergada: 'Postergada',
}

export function StatusBadge({ status, label, className = '' }: StatusBadgeProps) {
  const { color, bg } = STATUS_COLOR_MAP[status] ?? DEFAULT_COLOR
  const displayLabel = label ?? STATUS_LABEL_MAP[status] ?? status

  return (
    <span
      className={[
        'inline-flex items-center gap-[5px] rounded-full px-[9px] py-[4px] text-[11px] font-bold whitespace-nowrap',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      style={{ color, backgroundColor: bg }}
    >
      {displayLabel}
    </span>
  )
}
