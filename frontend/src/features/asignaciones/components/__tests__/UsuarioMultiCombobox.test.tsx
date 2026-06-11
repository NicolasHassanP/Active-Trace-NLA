/**
 * UsuarioMultiCombobox tests — TDD suite.
 *
 * Covers:
 *   - Renders search input initially with empty value
 *   - Shows dropdown results when query is typed
 *   - Selecting a user adds a chip and calls onChange with updated array
 *   - Selecting multiple users accumulates in the array
 *   - Removing a chip calls onChange with the id removed
 *   - Already-selected users are filtered from results
 *   - Shows empty state when no results
 *   - searchHook prop: injected hook is called and overrides default
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, useState } from 'react'
import UsuarioMultiCombobox from '../UsuarioMultiCombobox'
import type { UsuarioAsignable } from '../../types'

// Mock the default hook
vi.mock('../../hooks/asignacionHooks', () => ({
  useBuscarUsuariosAsignables: vi.fn(),
}))

import { useBuscarUsuariosAsignables } from '../../hooks/asignacionHooks'

const mockHook = vi.mocked(useBuscarUsuariosAsignables)

const sampleUsuarios: UsuarioAsignable[] = [
  { id: 'uuid-1', nombre: 'Ana', apellidos: 'García', email: 'ana@test.com' },
  { id: 'uuid-2', nombre: 'Pedro', apellidos: 'López', email: 'pedro@test.com' },
]

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

const emptyResult = {
  data: [],
  isFetching: false,
  isSuccess: true,
  isError: false,
} as unknown as ReturnType<typeof useBuscarUsuariosAsignables>

beforeEach(() => {
  mockHook.mockReturnValue(emptyResult)
})

// ── initial render ──────────────────────────────────────────────────────────

describe('UsuarioMultiCombobox — initial state', () => {
  it('renders search input when value is empty', () => {
    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByTestId('usuario-multi-combobox-input')).toBeTruthy()
  })

  it('does not show dropdown when query is empty', () => {
    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )
    expect(screen.queryByTestId('usuario-multi-combobox-dropdown')).toBeNull()
  })

  it('shows no chips when value is empty', () => {
    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )
    expect(screen.queryByTestId('multi-chip-uuid-1')).toBeNull()
  })
})

// ── search results ──────────────────────────────────────────────────────────

describe('UsuarioMultiCombobox — search results', () => {
  it('shows dropdown with results when query is typed', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )

    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'ana' },
    })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-multi-combobox-dropdown')).toBeTruthy()
    })
  })

  it('shows empty state when no results returned', async () => {
    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )

    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'zzz' },
    })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-multi-combobox-empty')).toBeTruthy()
    })
  })

  it('filters out already-selected users from dropdown', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    // uuid-1 already selected
    render(
      <UsuarioMultiCombobox value={['uuid-1']} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )

    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'ana' },
    })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-multi-option-uuid-1')).toBeNull()
      expect(screen.queryByTestId('usuario-multi-option-uuid-2')).toBeTruthy()
    })
  })
})

// ── selection — adds chip, updates array ────────────────────────────────────

describe('UsuarioMultiCombobox — selection', () => {
  it('calls onChange with [id] when first user is selected', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} />,
      { wrapper: makeWrapper() },
    )

    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'ana' },
    })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-multi-option-uuid-1')).toBeTruthy()
    })

    fireEvent.mouseDown(screen.getByTestId('usuario-multi-option-uuid-1'))

    expect(onChange).toHaveBeenCalledWith(['uuid-1'])
  })

  it('accumulates multiple selections in the array', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    // Stateful wrapper simulating controlled form field
    function Wrapper() {
      const [ids, setIds] = useState<string[]>([])
      return (
        <UsuarioMultiCombobox
          value={ids}
          onChange={setIds}
          data-testid="multi"
        />
      )
    }

    render(<Wrapper />, { wrapper: makeWrapper() })

    // Select uuid-1
    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'ana' },
    })
    await waitFor(() => expect(screen.queryByTestId('usuario-multi-option-uuid-1')).toBeTruthy())
    fireEvent.mouseDown(screen.getByTestId('usuario-multi-option-uuid-1'))

    // uuid-1 chip appears
    await waitFor(() => expect(screen.queryByTestId('multi-chip-uuid-1')).toBeTruthy())

    // Select uuid-2
    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'pedro' },
    })
    await waitFor(() => expect(screen.queryByTestId('usuario-multi-option-uuid-2')).toBeTruthy())
    fireEvent.mouseDown(screen.getByTestId('usuario-multi-option-uuid-2'))

    await waitFor(() => {
      expect(screen.queryByTestId('multi-chip-uuid-1')).toBeTruthy()
      expect(screen.queryByTestId('multi-chip-uuid-2')).toBeTruthy()
    })
  })

  it('shows chip with label after selection', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    function Wrapper() {
      const [ids, setIds] = useState<string[]>([])
      return <UsuarioMultiCombobox value={ids} onChange={setIds} />
    }

    render(<Wrapper />, { wrapper: makeWrapper() })

    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'ana' },
    })
    await waitFor(() => expect(screen.queryByTestId('usuario-multi-option-uuid-1')).toBeTruthy())
    fireEvent.mouseDown(screen.getByTestId('usuario-multi-option-uuid-1'))

    await waitFor(() => {
      const chip = screen.queryByTestId('multi-chip-uuid-1')
      expect(chip).toBeTruthy()
      expect(chip?.textContent).toContain('García')
    })
  })
})

// ── removal — chip remove button ────────────────────────────────────────────

describe('UsuarioMultiCombobox — removal', () => {
  it('removes a chip and calls onChange without that id', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()

    function Wrapper() {
      const [ids, setIds] = useState<string[]>([])
      return (
        <UsuarioMultiCombobox
          value={ids}
          onChange={(next) => { setIds(next); onChange(next) }}
        />
      )
    }

    render(<Wrapper />, { wrapper: makeWrapper() })

    // Select uuid-1
    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'ana' },
    })
    await waitFor(() => expect(screen.queryByTestId('usuario-multi-option-uuid-1')).toBeTruthy())
    fireEvent.mouseDown(screen.getByTestId('usuario-multi-option-uuid-1'))
    await waitFor(() => expect(screen.queryByTestId('multi-chip-uuid-1')).toBeTruthy())

    // Remove chip
    fireEvent.click(screen.getByTestId('multi-chip-remove-uuid-1'))

    await waitFor(() => {
      expect(screen.queryByTestId('multi-chip-uuid-1')).toBeNull()
    })
    // Last onChange call after removal should be empty array
    const calls = onChange.mock.calls
    const lastCall = calls[calls.length - 1][0] as string[]
    expect(lastCall).not.toContain('uuid-1')
  })
})

// ── injected searchHook ──────────────────────────────────────────────────────

describe('UsuarioMultiCombobox — searchHook injection', () => {
  it('uses injected searchHook results instead of default hook', async () => {
    const customUsuarios: UsuarioAsignable[] = [
      { id: 'custom-1', nombre: 'Lucia', apellidos: 'Martínez', email: 'lucia@test.com' },
    ]
    const customHook = vi.fn().mockReturnValue({
      data: customUsuarios,
      isFetching: false,
      isLoading: false,
    })

    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} searchHook={customHook} />,
      { wrapper: makeWrapper() },
    )

    fireEvent.change(screen.getByTestId('usuario-multi-combobox-input'), {
      target: { value: 'lucia' },
    })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-multi-option-custom-1')).toBeTruthy()
    })

    // Default hook is called with empty string (dormant), custom hook is called with live query
    expect(customHook).toHaveBeenCalled()
    // uuid-1/uuid-2 from default hook should not appear
    expect(screen.queryByTestId('usuario-multi-option-uuid-1')).toBeNull()
  })
})

// ── error display ─────────────────────────────────────────────────────────────

describe('UsuarioMultiCombobox — error', () => {
  it('shows error message when error prop is provided', () => {
    const onChange = vi.fn()
    render(
      <UsuarioMultiCombobox value={[]} onChange={onChange} error="Seleccioná al menos un usuario" />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByText('Seleccioná al menos un usuario')).toBeTruthy()
  })
})
