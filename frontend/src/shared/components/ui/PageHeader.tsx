import { type ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div>
        <h1 className="text-[22px] font-extrabold tracking-[-0.6px] text-ink">{title}</h1>
        {subtitle && (
          <p className="text-[13.5px] text-mut mt-1 max-w-[640px]">{subtitle}</p>
        )}
      </div>
      {actions && (
        <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>
      )}
    </div>
  )
}
