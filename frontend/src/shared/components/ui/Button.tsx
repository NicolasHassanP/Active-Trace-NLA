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
    'bg-ind2 text-white hover:bg-[#3730a3] border border-ind2 shadow-[0_3px_8px_rgba(67,56,202,.35)]',
  secondary:
    'bg-white text-[#3a4253] hover:bg-[#f6f7fb] border border-line',
  danger:
    'bg-red-600 text-white hover:bg-red-700 border border-red-600',
  ghost:
    'bg-transparent text-mut hover:bg-[#f4f4f8] border border-transparent',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'px-[11px] py-[7px] text-[12.5px] rounded-[9px]',
  md: 'px-[14px] py-[9px] text-[13px] rounded-btn',
  lg: 'px-[18px] py-[11px] text-[13.5px] rounded-btn',
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
    'inline-flex items-center gap-[7px] font-bold whitespace-nowrap transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ind',
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
