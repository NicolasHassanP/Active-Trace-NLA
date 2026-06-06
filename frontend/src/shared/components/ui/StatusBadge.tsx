/**
 * StatusBadge — domain-aware badge that maps status strings to Tailwind color classes.
 * Mappings:
 *   vigente | activo | al_dia          → green
 *   vencido | inactivo | atrasado      → red
 *   futuro  | pendiente                → yellow
 *   sin_datos | cancelado             → gray
 * Unknown statuses fall back to gray.
 * < 200 LOC. No `any`. Only Tailwind v3.
 */

interface StatusBadgeProps {
  status: string
  /** Override the display label. Defaults to the status value itself. */
  label?: string
  className?: string
}

type ColorClasses = { bg: string; text: string }

const STATUS_COLOR_MAP: Record<string, ColorClasses> = {
  // green — active / current / on-track
  vigente:   { bg: 'bg-green-100', text: 'text-green-700' },
  activo:    { bg: 'bg-green-100', text: 'text-green-700' },
  al_dia:    { bg: 'bg-green-100', text: 'text-green-800' },

  // red — overdue / inactive
  vencido:   { bg: 'bg-red-100', text: 'text-red-800' },
  inactivo:  { bg: 'bg-red-100', text: 'text-red-800' },
  atrasado:  { bg: 'bg-red-100', text: 'text-red-800' },

  // yellow — future / pending
  futuro:    { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  futura:    { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  pendiente: { bg: 'bg-yellow-100', text: 'text-yellow-700' },

  // gray — no data / cancelled / default
  sin_datos: { bg: 'bg-gray-100', text: 'text-gray-600' },
  cancelado: { bg: 'bg-gray-100', text: 'text-gray-600' },
}

const DEFAULT_COLOR: ColorClasses = { bg: 'bg-gray-100', text: 'text-gray-600' }

const STATUS_LABEL_MAP: Record<string, string> = {
  vigente:   'Vigente',
  activo:    'Activo',
  al_dia:    'Al día',
  vencido:   'Vencido',
  inactivo:  'Inactivo',
  atrasado:  'Atrasado',
  futuro:    'Futuro',
  futura:    'Futura',
  pendiente: 'Pendiente',
  sin_datos: 'Sin datos',
  cancelado: 'Cancelado',
}

export function StatusBadge({ status, label, className = '' }: StatusBadgeProps) {
  const colors = STATUS_COLOR_MAP[status] ?? DEFAULT_COLOR
  const displayLabel = label ?? STATUS_LABEL_MAP[status] ?? status

  const classes = [
    'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
    colors.bg,
    colors.text,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return <span className={classes}>{displayLabel}</span>
}
