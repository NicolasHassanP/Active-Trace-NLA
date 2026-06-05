/**
 * PadronPage render tests — tests render states.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PadronPage from '../PadronPage'
import * as padronService from '../../services/padronService'
import type { PadronRowDTO } from '../../types'

vi.mock('../../services/padronService')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

const wrapper = ({ children }: { children: React.ReactNode }) =>
  createElement(QueryClientProvider, {
    client: new QueryClient({ defaultOptions: { queries: { retry: false } } }),
  }, children)

const sampleRows: PadronRowDTO[] = [
  { nombre: 'Ana', apellidos: 'Paz', email: 'a@t.com', comision: 'A', regional: 'BUE' },
]

beforeEach(() => vi.clearAllMocks())

describe('PadronPage', () => {
  it('renders heading and context selector initially', () => {
    render(<PadronPage />, { wrapper })
    expect(screen.getByText('Importación de Padrón')).toBeInTheDocument()
    expect(screen.getByTestId('materia-id-input')).toBeInTheDocument()
    expect(screen.getByTestId('cohorte-id-input')).toBeInTheDocument()
  })

  it('shows prompt to enter materia/cohorte before context is set', () => {
    render(<PadronPage />, { wrapper })
    expect(screen.getByText(/Ingresá la materia y la cohorte/i)).toBeInTheDocument()
  })

  it('reveals import section once materia and cohorte are entered', () => {
    render(<PadronPage />, { wrapper })
    fireEvent.change(screen.getByTestId('materia-id-input'), { target: { value: 'm1' } })
    fireEvent.change(screen.getByTestId('cohorte-id-input'), { target: { value: 'c1' } })
    expect(screen.getByTestId('padron-file-input')).toBeInTheDocument()
    expect(screen.getByTestId('vaciar-padron-btn')).toBeInTheDocument()
  })

  it('shows inline 422 error after preview fails', async () => {
    vi.mocked(padronService.previewPadron).mockRejectedValue({
      status: 422,
      detail: 'columna email faltante',
    })
    render(<PadronPage />, { wrapper })
    fireEvent.change(screen.getByTestId('materia-id-input'), { target: { value: 'm1' } })
    fireEvent.change(screen.getByTestId('cohorte-id-input'), { target: { value: 'c1' } })

    const file = new File(['bad'], 'bad.csv', { type: 'text/csv' })
    const input = screen.getByTestId('padron-file-input')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('columna email faltante'),
    )
  })

  it('shows preview table and confirm button after successful preview', async () => {
    vi.mocked(padronService.previewPadron).mockResolvedValue(sampleRows)
    render(<PadronPage />, { wrapper })
    fireEvent.change(screen.getByTestId('materia-id-input'), { target: { value: 'm1' } })
    fireEvent.change(screen.getByTestId('cohorte-id-input'), { target: { value: 'c1' } })

    const file = new File(['ok'], 'ok.csv', { type: 'text/csv' })
    const input = screen.getByTestId('padron-file-input')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)

    await waitFor(() => expect(screen.getByTestId('confirm-import')).toBeInTheDocument())
    expect(screen.getByText('Ana')).toBeInTheDocument()
  })
})
