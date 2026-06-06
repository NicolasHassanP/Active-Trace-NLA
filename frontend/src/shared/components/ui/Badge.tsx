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
  success: 'text-ok bg-okBg',
  warning: 'text-amber2 bg-amberBg',
  danger:  'text-warn bg-warnBg',
  info:    'text-ind2 bg-indBg',
  gray:    'text-mut bg-[#f1f2f5]',
  indigo:  'text-ind2 bg-indBg',
  purple:  'text-vio bg-vioBg',
  orange:  'text-amber2 bg-amberBg',
}

export function Badge({ variant = 'gray', children, className = '' }: BadgeProps) {
  const classes = [
    'inline-flex items-center gap-[5px] rounded-full px-[9px] py-[4px] text-[11px] font-bold whitespace-nowrap',
    VARIANT_CLASSES[variant],
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return <span className={classes}>{children}</span>
}
