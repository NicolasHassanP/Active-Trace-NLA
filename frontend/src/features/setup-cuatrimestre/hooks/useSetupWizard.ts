/**
 * useSetupWizard — manages the step-by-step state of the Setup Cuatrimestre wizard.
 *
 * Rules (from spec FL-03):
 * - Sequential advance: the user can only advance when the current step succeeds.
 * - Error in a step: marks step as 'error', does NOT advance.
 * - All steps completed: wizard marks itself as completado.
 *
 * Pure state management — no API calls here.
 * Services are called by the calling component, which then calls completeStep / errorStep.
 *
 * Task 7.2. Strict TDD: tests written first in useSetupWizard.test.ts.
 */
import { useReducer } from 'react'
import type { SetupWizardState, SetupPasoState } from '../types'
import { SETUP_PASOS } from '../types'

// ---------------------------------------------------------------------------
// State factory
// ---------------------------------------------------------------------------

function buildInitialState(): SetupWizardState {
  const pasos: SetupPasoState[] = SETUP_PASOS.map((p) => ({
    id: p.id,
    estado: 'pendiente',
  }))
  return { pasos, pasoActivo: 0, completado: false }
}

// ---------------------------------------------------------------------------
// Reducer actions
// ---------------------------------------------------------------------------

type Action =
  | { type: 'COMPLETE_STEP'; index: number }
  | { type: 'ERROR_STEP'; index: number; error: string }
  | { type: 'RETRY_STEP'; index: number }

function reducer(state: SetupWizardState, action: Action): SetupWizardState {
  switch (action.type) {
    case 'COMPLETE_STEP': {
      const pasos = state.pasos.map((p, i) =>
        i === action.index ? { ...p, estado: 'completado' as const, error: undefined } : p,
      )
      const nextActivo = action.index + 1
      const completado = pasos.every((p) => p.estado === 'completado')
      return {
        ...state,
        pasos,
        pasoActivo: nextActivo,
        completado,
      }
    }
    case 'ERROR_STEP': {
      const pasos = state.pasos.map((p, i) =>
        i === action.index ? { ...p, estado: 'error' as const, error: action.error } : p,
      )
      return { ...state, pasos, completado: false }
      // pasoActivo stays the same — error does NOT advance
    }
    case 'RETRY_STEP': {
      const pasos = state.pasos.map((p, i) =>
        i === action.index ? { ...p, estado: 'pendiente' as const, error: null } : p,
      )
      return { ...state, pasos, pasoActivo: action.index }
    }
    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseSetupWizardReturn {
  state: SetupWizardState
  /** Mark step at index as completed and advance to next */
  completeStep: (index: number) => void
  /** Mark step at index as error (does not advance) */
  errorStep: (index: number, error: string) => void
  /** Reset step at index back to pendiente (retry) */
  retryStep: (index: number) => void
}

export function useSetupWizard(): UseSetupWizardReturn {
  const [state, dispatch] = useReducer(reducer, undefined, buildInitialState)

  function completeStep(index: number) {
    dispatch({ type: 'COMPLETE_STEP', index })
  }

  function errorStep(index: number, error: string) {
    dispatch({ type: 'ERROR_STEP', index, error })
  }

  function retryStep(index: number) {
    dispatch({ type: 'RETRY_STEP', index })
  }

  return { state, completeStep, errorStep, retryStep }
}
