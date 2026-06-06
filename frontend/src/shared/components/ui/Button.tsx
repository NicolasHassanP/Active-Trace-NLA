/**
 * Button — shared UI component with variant and size support.
 * Variants: primary | secondary | danger | ghost
 * Sizes: sm | md | lg
 * Supports disabled and isLoading states.
 * < 200 LOC. No `any`. Only Tailwind v3.
 */
import { type ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-indigo-600 text-white hover:bg-indigo-700 border border-indigo-600 focus:ring-indigo-500',
  secondary:
    'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300 focus:ring-indigo-500',
  danger:
    'bg-red-600 text-white hover:bg-red-700 border border-red-600 focus:ring-red-500',
  ghost:
    'bg-transparent text-gray-600 hover:bg-gray-100 border border-transparent focus:ring-gray-400',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded',
  md: 'px-4 py-2 text-sm rounded',
  lg: 'px-5 py-2.5 text-base rounded-md',
}

function Spinner() {
  return (
    <svg
      className="mr-2 inline-block h-4 w-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || isLoading

  const classes = [
    'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    isDisabled ? 'opacity-50 cursor-not-allowed' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button {...rest} disabled={isDisabled} className={classes}>
      {isLoading && <Spinner />}
      {children}
    </button>
  )
}
