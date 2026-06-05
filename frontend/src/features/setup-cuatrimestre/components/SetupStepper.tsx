/**
 * SetupStepper — visual progress indicator for the setup wizard.
 * Displays ordered steps with estado (pendiente / completado / error).
 * Task 7.3. < 200 LOC. No class components, no `any`.
 */
import type { SetupPasoState } from '../types'
import { SETUP_PASOS } from '../types'

interface StepperProps {
  pasos: SetupPasoState[]
  pasoActivo: number
}

function StepIcon({ estado, index }: { estado: SetupPasoState['estado']; index: number }) {
  if (estado === 'completado') {
    return (
      <span
        aria-label="completado"
        className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500 text-white text-sm font-bold"
      >
        ✓
      </span>
    )
  }
  if (estado === 'error') {
    return (
      <span
        aria-label="error"
        className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-white text-sm font-bold"
      >
        ✗
      </span>
    )
  }
  return (
    <span
      aria-label="pendiente"
      className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-gray-300 bg-white text-gray-500 text-sm font-semibold"
    >
      {index + 1}
    </span>
  )
}

export default function SetupStepper({ pasos, pasoActivo }: StepperProps) {
  return (
    <ol aria-label="Pasos del setup" className="space-y-3">
      {pasos.map((pasoState, index) => {
        const meta = SETUP_PASOS[index]
        const isActive = index === pasoActivo
        return (
          <li
            key={pasoState.id}
            data-testid={`step-${pasoState.id}`}
            className={[
              'flex items-start gap-3 rounded-lg border p-3',
              isActive && pasoState.estado !== 'completado'
                ? 'border-indigo-400 bg-indigo-50'
                : pasoState.estado === 'completado'
                ? 'border-green-200 bg-green-50'
                : pasoState.estado === 'error'
                ? 'border-red-200 bg-red-50'
                : 'border-gray-200 bg-white opacity-60',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            <StepIcon estado={pasoState.estado} index={index} />
            <div className="flex-1 min-w-0">
              <p
                className={`text-sm font-medium ${
                  pasoState.estado === 'completado'
                    ? 'text-green-700'
                    : pasoState.estado === 'error'
                    ? 'text-red-700'
                    : isActive
                    ? 'text-indigo-700'
                    : 'text-gray-500'
                }`}
              >
                {meta?.label ?? pasoState.id}
              </p>
              {pasoState.estado !== 'completado' && meta?.descripcion && (
                <p className="text-xs text-gray-500 mt-0.5">{meta.descripcion}</p>
              )}
              {pasoState.estado === 'error' && pasoState.error && (
                <p role="alert" className="text-xs text-red-600 mt-1">
                  {pasoState.error}
                </p>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
