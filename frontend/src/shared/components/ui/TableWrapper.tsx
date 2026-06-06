import { type ReactNode } from 'react'

interface TableWrapperProps {
  children: ReactNode
  className?: string
}

export function TableWrapper({ children, className = '' }: TableWrapperProps) {
  return (
    <div className={['w-full overflow-hidden', className].filter(Boolean).join(' ')}>
      <table className="w-full border-collapse [&_th]:text-[11px] [&_th]:font-bold [&_th]:tracking-[0.4px] [&_th]:uppercase [&_th]:text-faint [&_th]:py-[11px] [&_th]:px-[14px] [&_th]:border-b [&_th]:border-line [&_th]:whitespace-nowrap [&_td]:py-[11px] [&_td]:px-[14px] [&_td]:border-b [&_td]:border-line2 [&_td]:align-middle [&_tbody_tr:last-child_td]:border-b-0 [&_tbody_tr:hover]:bg-[#fafbff] [&_.num]:tabular-nums [&_.num]:font-bold">
        {children}
      </table>
    </div>
  )
}
