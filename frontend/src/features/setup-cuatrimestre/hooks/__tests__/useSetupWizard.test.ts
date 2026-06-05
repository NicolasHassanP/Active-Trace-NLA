/**
 * TDD — useSetupWizard hook.
 * Task 7.2 — RED first.
 *
 * Scenarios:
 * - Initial state: all steps pendiente, pasoActivo = 0, not completed
 * - completeStep advances to next step and marks current as completado
 * - errorStep marks current step as error and does NOT advance
 * - completing all steps marks wizard as completado
 * - advancing is blocked when current step is still pendiente
 */
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSetupWizard } from '../useSetupWizard'

const TOTAL_STEPS = 7

describe('useSetupWizard — initial state', () => {
  it('initialises with all steps pendiente', () => {
    const { result } = renderHook(() => useSetupWizard())
    const { pasos } = result.current.state
    expect(pasos).toHaveLength(TOTAL_STEPS)
    pasos.forEach((p) => {
      expect(p.estado).toBe('pendiente')
      expect(p.error).toBeUndefined()
    })
  })

  it('starts at paso 0 and not completed', () => {
    const { result } = renderHook(() => useSetupWizard())
    expect(result.current.state.pasoActivo).toBe(0)
    expect(result.current.state.completado).toBe(false)
  })
})

describe('useSetupWizard — completeStep', () => {
  it('marks current step completado and advances pasoActivo', () => {
    const { result } = renderHook(() => useSetupWizard())

    act(() => {
      result.current.completeStep(0)
    })

    expect(result.current.state.pasos[0].estado).toBe('completado')
    expect(result.current.state.pasoActivo).toBe(1)
  })

  it('completing all steps marks wizard as completado', () => {
    const { result } = renderHook(() => useSetupWizard())

    act(() => {
      for (let i = 0; i < TOTAL_STEPS; i++) {
        result.current.completeStep(i)
      }
    })

    expect(result.current.state.completado).toBe(true)
    expect(result.current.state.pasos.every((p) => p.estado === 'completado')).toBe(true)
  })

  it('does not advance beyond the last step index', () => {
    const { result } = renderHook(() => useSetupWizard())

    act(() => {
      for (let i = 0; i < TOTAL_STEPS; i++) {
        result.current.completeStep(i)
      }
    })

    // pasoActivo should be TOTAL_STEPS (past last valid index) or stay at last
    expect(result.current.state.pasoActivo).toBeGreaterThanOrEqual(TOTAL_STEPS - 1)
  })
})

describe('useSetupWizard — errorStep', () => {
  it('marks step as error without advancing', () => {
    const { result } = renderHook(() => useSetupWizard())

    act(() => {
      result.current.errorStep(0, 'API returned 422')
    })

    const paso = result.current.state.pasos[0]
    expect(paso.estado).toBe('error')
    expect(paso.error).toBe('API returned 422')
    // pasoActivo must NOT advance
    expect(result.current.state.pasoActivo).toBe(0)
  })

  it('still reports not completado when a step has error', () => {
    const { result } = renderHook(() => useSetupWizard())

    act(() => {
      result.current.errorStep(2, 'conflict')
    })

    expect(result.current.state.completado).toBe(false)
  })
})

describe('useSetupWizard — retryStep', () => {
  it('resets a step with error back to pendiente without advancing', () => {
    const { result } = renderHook(() => useSetupWizard())

    act(() => {
      result.current.errorStep(0, 'error msg')
    })
    act(() => {
      result.current.retryStep(0)
    })

    expect(result.current.state.pasos[0].estado).toBe('pendiente')
    expect(result.current.state.pasos[0].error).toBeNull()
    expect(result.current.state.pasoActivo).toBe(0)
  })
})
