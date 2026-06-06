/**
 * Card — container with sub-components CardHeader, CardTitle, CardContent, CardFooter.
 * < 200 LOC. No `any`. Only Tailwind v3.
 */
import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={['rounded-xl border border-gray-200 bg-white shadow-sm', className]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: ReactNode
  className?: string
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return (
    <div
      className={['flex items-center justify-between px-6 py-4 border-b border-gray-100', className]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}

interface CardTitleProps {
  children: ReactNode
  className?: string
}

export function CardTitle({ children, className = '' }: CardTitleProps) {
  return (
    <h3
      className={['text-base font-semibold text-gray-900', className]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </h3>
  )
}

interface CardContentProps {
  children: ReactNode
  className?: string
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return (
    <div className={['px-6 py-4', className].filter(Boolean).join(' ')}>
      {children}
    </div>
  )
}

interface CardFooterProps {
  children: ReactNode
  className?: string
}

export function CardFooter({ children, className = '' }: CardFooterProps) {
  return (
    <div
      className={[
        'flex items-center justify-between px-6 py-3 border-t border-gray-100 bg-gray-50 rounded-b-xl',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}
