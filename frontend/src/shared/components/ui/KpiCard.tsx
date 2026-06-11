import { type ReactNode } from 'react'

type KpiVariant = 'ind' | 'warn' | 'ok' | 'amber'

interface KpiCardProps {
  icon: ReactNode
  value: string | number
  label: string
  sub?: string
  variant?: KpiVariant
}

const CHIP_CLASSES: Record<KpiVariant, string> = {
  ind:   'bg-indBg text-ind',
  warn:  'bg-warnBg text-warn',
  ok:    'bg-okBg text-ok',
  amber: 'bg-amberBg text-amber2',
}

export function KpiCard({ icon, value, label, sub, variant = 'ind' }: KpiCardProps) {
  return (
    <div className="bg-white border border-line rounded-[14px] p-4 shadow-card">
      <div className={['w-[34px] h-[34px] rounded-[10px] flex items-center justify-center', CHIP_CLASSES[variant]].join(' ')}>
        {icon}
      </div>
      <p className="text-[26px] font-extrabold tracking-[-1px] text-ink mt-[11px]">{value}</p>
      <p className="text-[12.5px] text-mut font-semibold mt-[1px]">{label}</p>
      {sub && <p className="text-[11.5px] text-faint mt-[7px]">{sub}</p>}
    </div>
  )
}
