/**
 * NuevoHiloForm component tests.
 * Verifies: renders with UsuarioCombobox instead of UUID input,
 * selecting a user sets destinatario_id, submit with valid destinatario works,
 * submit without destinatario shows validation error.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { NuevoHiloForm } from '../NuevoHiloForm'
import type { UsuarioAsignable } from '@/features/asignaciones/types'

// Mock the mensajeriaHooks — keep real hook shapes, stub implementations
vi.mock('../../hooks/mensajeriaHooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../hooks/mensajeriaHooks')>()
  return {
    ...actual,
    useIniciarHilo: vi.fn(),
    useBuscarUsuariosInbox: vi.fn(),
  }
})

import { useIniciarHilo, useBuscarUsuariosInbox } from '../../hooks/mensajeriaHooks'

const sampleUsuario: UsuarioAsignable = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  nombre: 'Ana',
  apellidos: 'García',
  email: 'ana@test.com',
}

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useIniciarHilo).mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    isError: false,
    isSuccess: false,
    isIdle: true,
    error: null,
    data: undefined,
    mutate: vi.fn(),
    reset: vi.fn(),
    context: undefined,
    failureCount: 0,
    failureReason: null,
    isPaused: false,
    status: 'idle',
    variables: undefined,
    submittedAt: 0,
  } as ReturnType<typeof useIniciarHilo>)
  vi.mocked(useBuscarUsuariosInbox).mockReturnValue(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    { data: [] as UsuarioAsignable[], isLoading: false, isFetching: false } as any,
  )
})

describe('NuevoHiloForm — render', () => {
  it('renders the combobox for destinatario (not a raw UUID input)', () => {
    render(<NuevoHiloForm onSuccess={vi.fn()} onCancel={vi.fn()} />, { wrapper: makeWrapper() })
    // Should show the combobox search input, not the old UUID placeholder
    expect(screen.getByTestId('usuario-combobox')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('UUID del destinatario')).not.toBeInTheDocument()
  })

  it('renders asunto and cuerpo fields', () => {
    render(<NuevoHiloForm onSuccess={vi.fn()} onCancel={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByPlaceholderText('Asunto (opcional)')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Escribí tu mensaje...')).toBeInTheDocument()
  })

  it('renders Enviar and Cancelar buttons', () => {
    render(<NuevoHiloForm onSuccess={vi.fn()} onCancel={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByRole('button', { name: /Enviar/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cancelar/i })).toBeInTheDocument()
  })
})

describe('NuevoHiloForm — selecting a user', () => {
  it('selecting a user from the combobox dropdown sets destinatario', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useBuscarUsuariosInbox).mockReturnValue({ data: [sampleUsuario], isLoading: false, isFetching: false } as any)

    render(<NuevoHiloForm onSuccess={vi.fn()} onCancel={vi.fn()} />, { wrapper: makeWrapper() })

    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'Ana' } })

    // Wait for debounce + dropdown
    await waitFor(() =>
      expect(screen.getByTestId(`usuario-option-${sampleUsuario.id}`)).toBeInTheDocument()
    )

    fireEvent.mouseDown(screen.getByTestId(`usuario-option-${sampleUsuario.id}`))

    // After selection, the chip with the user's name should appear
    await waitFor(() =>
      expect(screen.getByTestId('usuario-combobox-selected')).toHaveTextContent('Ana')
    )
  })
})

describe('NuevoHiloForm — submit', () => {
  it('shows validation error when submitted without destinatario', async () => {
    render(<NuevoHiloForm onSuccess={vi.fn()} onCancel={vi.fn()} />, { wrapper: makeWrapper() })
    // Fill cuerpo but leave destinatario empty
    fireEvent.change(screen.getByPlaceholderText('Escribí tu mensaje...'), {
      target: { value: 'Hola!' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Enviar/i }))
    await waitFor(() =>
      expect(screen.getByText(/Seleccioná un destinatario/i)).toBeInTheDocument()
    )
  })

  it('calls iniciarHilo with correct destinatario_id on valid submit', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({})
    vi.mocked(useIniciarHilo).mockReturnValue({
      mutateAsync,
      isPending: false,
      isError: false,
      isSuccess: false,
      isIdle: true,
      error: null,
      data: undefined,
      mutate: vi.fn(),
      reset: vi.fn(),
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isPaused: false,
      status: 'idle',
      variables: undefined,
      submittedAt: 0,
    } as ReturnType<typeof useIniciarHilo>)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useBuscarUsuariosInbox).mockReturnValue({ data: [sampleUsuario], isLoading: false, isFetching: false } as any)

    const onSuccess = vi.fn()
    render(<NuevoHiloForm onSuccess={onSuccess} onCancel={vi.fn()} />, { wrapper: makeWrapper() })

    // Select a user
    const input = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(input, { target: { value: 'Ana' } })
    await waitFor(() =>
      expect(screen.getByTestId(`usuario-option-${sampleUsuario.id}`)).toBeInTheDocument()
    )
    fireEvent.mouseDown(screen.getByTestId(`usuario-option-${sampleUsuario.id}`))

    // Fill cuerpo
    fireEvent.change(screen.getByPlaceholderText('Escribí tu mensaje...'), {
      target: { value: 'Hola Ana!' },
    })

    fireEvent.click(screen.getByRole('button', { name: /Enviar/i }))

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ destinatario_id: sampleUsuario.id }),
      )
    )
  })

  it('calls onCancel when Cancelar is clicked', () => {
    const onCancel = vi.fn()
    render(<NuevoHiloForm onSuccess={vi.fn()} onCancel={onCancel} />, { wrapper: makeWrapper() })
    fireEvent.click(screen.getByRole('button', { name: /Cancelar/i }))
    expect(onCancel).toHaveBeenCalled()
  })
})
