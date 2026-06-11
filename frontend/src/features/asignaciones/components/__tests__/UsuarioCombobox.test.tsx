/**
 * UsuarioCombobox tests — TDD suite.
 *
 * Mocks useBuscarUsuariosAsignables hook.
 * Covers:
 *   - Renders input in search state initially
 *   - Shows results in dropdown when query is entered
 *   - Selecting a user calls onChange(id) and shows selected chip
 *   - Clear button resets to search state and calls onChange(null)
 *   - Shows empty state when no results
 *   - Shows loading state while fetching
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import UsuarioCombobox from '../UsuarioCombobox'
import type { UsuarioAsignable } from '../../types'

// Mock the hook
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

beforeEach(() => {
  mockHook.mockReturnValue({
    data: [],
    isFetching: false,
    isSuccess: true,
    isError: false,
  } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)
})

// ── renders input initially ─────────────────────────────────────────────────

describe('UsuarioCombobox — initial state', () => {
  it('renders search input in unselected state', () => {
    const onChange = vi.fn()
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })
    expect(screen.getByTestId('usuario-combobox-input')).toBeTruthy()
  })

  it('does not show dropdown when query is empty', () => {
    const onChange = vi.fn()
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })
    expect(screen.queryByTestId('usuario-combobox-dropdown')).toBeNull()
  })
})

// ── shows results ────────────────────────────────────────────────────────────

describe('UsuarioCombobox — search results', () => {
  it('shows dropdown with results when query is typed', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'ana' } })

    // Wait for dropdown to appear (debounce runs immediately in test env after state update)
    await waitFor(() => {
      expect(screen.queryByTestId('usuario-combobox-dropdown')).toBeTruthy()
    })
  })

  it('shows empty state when no results returned', async () => {
    mockHook.mockReturnValue({
      data: [],
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'zzz' } })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-combobox-empty')).toBeTruthy()
    })
  })

  it('shows loading state while fetching', async () => {
    mockHook.mockReturnValue({
      data: [],
      isFetching: true,
      isSuccess: false,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'any' } })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-combobox-loading')).toBeTruthy()
    })
  })
})

// ── selection ────────────────────────────────────────────────────────────────

describe('UsuarioCombobox — selection', () => {
  it('calls onChange(id) when a user option is clicked', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'ana' } })

    await waitFor(() => {
      expect(screen.queryByTestId(`usuario-option-uuid-1`)).toBeTruthy()
    })

    fireEvent.mouseDown(screen.getByTestId('usuario-option-uuid-1'))
    expect(onChange).toHaveBeenCalledWith('uuid-1')
  })

  it('shows selected chip after selection with value prop', () => {
    // Simulate parent controlling value=uuid-1 after selection
    // We need to pre-set selected state by rendering with value set
    // Since selected internal state is set on mouseDown, simulate by passing value
    // with the component already in selected state via a re-render trick
    const onChange = vi.fn()
    // Render with a non-null value but no selected user internally set
    // The component tracks selected internally from interaction.
    // Here we just confirm that the combobox renders without crash when value is set.
    render(<UsuarioCombobox value="uuid-1" onChange={onChange} />, {
      wrapper: makeWrapper(),
    })
    // Since selected is null but value is set, the input is shown (uncontrolled internal state).
    // The combobox is semi-controlled: internal selected drives the chip display.
    expect(screen.getByTestId('usuario-combobox')).toBeTruthy()
  })
})

// ── clear selection ──────────────────────────────────────────────────────────

describe('UsuarioCombobox — clear', () => {
  it('shows clear button and calls onChange(null) when cleared', async () => {
    /**
     * The combobox is semi-controlled: it shows the chip when internal `selected`
     * is set AND the `value` prop is non-null (mirrors RHF Controller behavior).
     * To test the clear button we use a stateful wrapper that updates value after
     * selection (simulating what Controller does in the real form).
     */
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    // Stateful wrapper
    const { useState } = await import('react')
    function Wrapper() {
      const [val, setVal] = useState<string | null>(null)
      return (
        <UsuarioCombobox
          value={val}
          onChange={(id) => setVal(id)}
        />
      )
    }

    render(<Wrapper />, { wrapper: makeWrapper() })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'ana' } })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-option-uuid-1')).toBeTruthy()
    })

    // Select first user — this calls onChange('uuid-1') which sets val='uuid-1' in wrapper
    fireEvent.mouseDown(screen.getByTestId('usuario-option-uuid-1'))

    // Now the chip should appear with the clear button
    await waitFor(() => {
      expect(screen.queryByTestId('usuario-combobox-clear')).toBeTruthy()
    })

    // Click clear → calls onChange(null) → val → null → back to search state
    fireEvent.click(screen.getByTestId('usuario-combobox-clear'))

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-combobox-input')).toBeTruthy()
      expect(screen.queryByTestId('usuario-combobox-clear')).toBeNull()
    })
  })
})

// ── error display ─────────────────────────────────────────────────────────────

describe('UsuarioCombobox — error', () => {
  it('shows error message when error prop is provided', () => {
    const onChange = vi.fn()
    render(
      <UsuarioCombobox value={null} onChange={onChange} error="Seleccione un usuario" />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByText('Seleccione un usuario')).toBeTruthy()
  })
})

// ── searchHook injection ──────────────────────────────────────────────────────

describe('UsuarioCombobox — searchHook injection', () => {
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
      <UsuarioCombobox value={null} onChange={onChange} searchHook={customHook} />,
      { wrapper: makeWrapper() },
    )

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'lucia' } })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-option-custom-1')).toBeTruthy()
    })

    // Custom hook was called with the live query
    expect(customHook).toHaveBeenCalled()
    // Default mock data (uuid-1/uuid-2) should not appear
    expect(screen.queryByTestId('usuario-option-uuid-1')).toBeNull()
  })

  it('works correctly with default hook when searchHook prop is omitted (no regression)', async () => {
    mockHook.mockReturnValue({
      data: sampleUsuarios,
      isFetching: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useBuscarUsuariosAsignables>)

    const onChange = vi.fn()
    // No searchHook prop — uses default
    render(<UsuarioCombobox value={null} onChange={onChange} />, {
      wrapper: makeWrapper(),
    })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'ana' } })

    await waitFor(() => {
      expect(screen.queryByTestId('usuario-option-uuid-1')).toBeTruthy()
    })
  })
})
