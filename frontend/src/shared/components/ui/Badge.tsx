/**
 * Badge — small inline status indicator.
 * Variants: success | warning | danger | info | gray | indigo | purple | orange
 * < 200 LOC. No `any`. Only Tailwind v3.
 */
import { type ReactNode } from 'react'

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'gray'
  | 'indigo'
  | 'purple'
  | 'orange'

interface BadgeProps {
  variant?: BadgeVariant
  children: ReactNode
  className?: string
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  success: 'bg-green-100 text-green-700',
  warning: 'bg-yellow-100 text-yellow-700',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-700',
  gray: 'bg-gray-100 text-gray-600',
  indigo: 'bg-indigo-100 text-indigo-700',
  purple: 'bg-purple-100 text-purple-700',
  orange: 'bg-orange-100 text-orange-700',
}

export function Badge({ variant = 'gray', children, className = '' }: BadgeProps) {
  const classes = [
    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
    VARIANT_CLASSES[variant],
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return <span className={classes}>{children}</span>
}
