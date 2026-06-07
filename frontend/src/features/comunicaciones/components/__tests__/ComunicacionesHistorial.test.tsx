/**
 * ComunicacionesHistorial component tests (C-27, Task 6.3).
 *
 * Covers:
 *   - Render de tabla con items
 *   - Estado vacío ("No tenés envíos todavía")
 *   - Estado de carga (spinner)
 *   - Estado de error (mensaje descriptivo)
 *   - Filtro de estado actualiza query key (via useMisEnvios mock)
 *   - Botón "Siguiente" deshabilitado al llegar al final (offset + limit >= total)
 *   - Botón "Anterior" deshabilitado en primera página
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ComunicacionesHistorial from '../ComunicacionesHistorial'
import * as hooks from '../../hooks/comunicacionHooks'
import type { MisEnviosResponse } from '../../types'

vi.mock('../../hooks/comunicacionHooks')

const mockUseMisEnvios = vi.mocked(hooks.useMisEnvios)

const wrapper = () => ({ children }: { children: React.ReactNode }) =>
  createElement(
    QueryClientProvider,
    { client: new QueryClient({ defaultOptions: { queries: { retry: false } } }) },
    children,
  )

const makeItem = (id: string) => ({
  id,
  lote_id: 'lote1',
  destinatario_email: `dest-${id}@test.com`,
  asunto: `Asunto ${id}`,
  cuerpo: 'Cuerpo',
  estado: 'Enviado' as const,
  creado_en: '2026-06-07T10:00:00Z',
  actualizado_en: '2026-06-07T10:00:00Z',
})

const mockDataConItems: MisEnviosResponse = {
  total: 3,
  offset: 0,
  limit: 20,
  items: [makeItem('m1'), makeItem('m2'), makeItem('m3')],
}

const mockDataVacia: MisEnviosResponse = {
  total: 0,
  offset: 0,
  limit: 20,
  items: [],
}

beforeEach(() => {
  vi.clearAllMocks()
})

// ---- Helper to stub useMisEnvios ----

function stubQuery(overrides: Partial<ReturnType<typeof hooks.useMisEnvios>>) {
  mockUseMisEnvios.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: false,
    isPending: true,
    ...overrides,
  } as any)
}

// ===========================================================================
// Task 6.3 — Tests del componente
// ===========================================================================

describe('ComunicacionesHistorial', () => {
  it('renders the historial panel', () => {
    stubQuery({ data: mockDataVacia, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('historial-panel')).toBeInTheDocument()
  })

  it('shows spinner while loading', () => {
    stubQuery({ isLoading: true, data: undefined })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('historial-loading')).toBeInTheDocument()
  })

  it('shows error message when query fails', () => {
    stubQuery({ isLoading: false, isError: true, data: undefined, error: new Error('Network error') })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('historial-error')).toBeInTheDocument()
    expect(screen.getByText(/no se pudo cargar/i)).toBeInTheDocument()
  })

  it('shows empty state when no items', () => {
    stubQuery({ data: mockDataVacia, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('historial-vacio')).toBeInTheDocument()
    expect(screen.getByText(/no tenés envíos todavía/i)).toBeInTheDocument()
  })

  it('renders table with items', () => {
    stubQuery({ data: mockDataConItems, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('historial-tabla')).toBeInTheDocument()
    expect(screen.getByText('Asunto m1')).toBeInTheDocument()
    expect(screen.getByText('Asunto m2')).toBeInTheDocument()
    expect(screen.getByText('Asunto m3')).toBeInTheDocument()
  })

  it('shows estado badge for each item', () => {
    stubQuery({ data: mockDataConItems, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    const badges = screen.getAllByText('Enviado')
    expect(badges.length).toBeGreaterThanOrEqual(3)
  })

  it('disables "Siguiente" when offset + limit >= total', () => {
    // total=3, offset=0, limit=20 → no hay más páginas
    stubQuery({ data: mockDataConItems, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('btn-siguiente')).toBeDisabled()
  })

  it('disables "Anterior" on first page', () => {
    stubQuery({ data: mockDataConItems, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('btn-anterior')).toBeDisabled()
  })

  it('enables "Siguiente" when more pages exist', () => {
    // total=25, offset=0, limit=20 → hay más páginas
    const dataConMas: MisEnviosResponse = {
      total: 25,
      offset: 0,
      limit: 20,
      items: Array.from({ length: 20 }, (_, i) => makeItem(`m${i}`)),
    }
    stubQuery({ data: dataConMas, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })
    expect(screen.getByTestId('btn-siguiente')).not.toBeDisabled()
  })

  it('calls useMisEnvios with estado filter when select changes', async () => {
    stubQuery({ data: mockDataVacia, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })

    const select = screen.getByTestId('estado-filtro')
    fireEvent.change(select, { target: { value: 'Enviado' } })

    await waitFor(() => {
      const calls = mockUseMisEnvios.mock.calls
      const lastCall = calls[calls.length - 1]
      expect(lastCall[0]).toMatchObject({ estado: 'Enviado' })
    })
  })

  it('resets offset to 0 when filter changes', async () => {
    // Simulate being on page 2 (offset=20), then changing filter
    const dataP2: MisEnviosResponse = {
      total: 45,
      offset: 20,
      limit: 20,
      items: Array.from({ length: 20 }, (_, i) => makeItem(`p2-m${i}`)),
    }
    stubQuery({ data: dataP2, isLoading: false, isError: false, isSuccess: true })
    render(<ComunicacionesHistorial />, { wrapper: wrapper() })

    // Click "Siguiente" to go to page 2
    const btnSiguiente = screen.getByTestId('btn-siguiente')
    fireEvent.click(btnSiguiente)

    // Now change the filter — offset should reset
    const select = screen.getByTestId('estado-filtro')
    fireEvent.change(select, { target: { value: 'Cancelado' } })

    await waitFor(() => {
      const calls = mockUseMisEnvios.mock.calls
      const lastCall = calls[calls.length - 1]
      expect(lastCall[0]).toMatchObject({ estado: 'Cancelado', offset: 0 })
    })
  })
})
