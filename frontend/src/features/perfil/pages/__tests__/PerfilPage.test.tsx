/**
 * PerfilPage render tests — loading/error states, edit + submit, 409 error handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PerfilPage from '../PerfilPage'
import * as perfilService from '../../services/perfilService'
import type { PerfilRead } from '../../types'

vi.mock('../../services/perfilService')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

const wrapper = ({ children }: { children: React.ReactNode }) =>
  createElement(QueryClientProvider, {
    client: new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }),
  }, children)

const samplePerfil: PerfilRead = {
  id: 'u-1',
  email: 'docente@test.com',
  nombre: 'Ana',
  apellidos: 'Gómez',
  dni: '30111222',
  cuil: '27-30111222-4',
  cbu: '0110599520000001234567',
  alias_cbu: 'ana.gomez.cbu',
  genero: 'F',
  legajo: 'L-001',
  legajo_profesional: 'MP-1234',
  banco: 'Nación',
  regional: 'BUE',
  facturador: true,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-06-01T00:00:00',
}

beforeEach(() => vi.clearAllMocks())

describe('PerfilPage', () => {
  it('shows loading state initially', () => {
    vi.mocked(perfilService.getPerfil).mockReturnValue(new Promise(() => {}))
    render(<PerfilPage />, { wrapper })
    expect(screen.getByText(/Cargando perfil/i)).toBeInTheDocument()
  })

  it('shows error state when the perfil fails to load', async () => {
    vi.mocked(perfilService.getPerfil).mockRejectedValue({ status: 401, detail: 'No autenticado' })
    render(<PerfilPage />, { wrapper })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('renders the form populated with the perfil and read-only fields', async () => {
    vi.mocked(perfilService.getPerfil).mockResolvedValue(samplePerfil)
    render(<PerfilPage />, { wrapper })
    await waitFor(() => expect(screen.getByDisplayValue('Ana')).toBeInTheDocument())
    expect(screen.getByDisplayValue('Gómez')).toBeInTheDocument()
    // Read-only fields shown disabled
    const cuilInput = screen.getByTestId('perfil-cuil') as HTMLInputElement
    expect(cuilInput.disabled).toBe(true)
    expect(cuilInput.value).toBe('27-30111222-4')
    const legajoInput = screen.getByTestId('perfil-legajo') as HTMLInputElement
    expect(legajoInput.disabled).toBe(true)
  })

  it('submits only editable fields and shows success toast', async () => {
    const { toast } = await import('sonner')
    vi.mocked(perfilService.getPerfil).mockResolvedValue(samplePerfil)
    vi.mocked(perfilService.updatePerfil).mockResolvedValue({ ...samplePerfil, nombre: 'Ana María' })
    render(<PerfilPage />, { wrapper })

    await waitFor(() => expect(screen.getByDisplayValue('Ana')).toBeInTheDocument())
    fireEvent.change(screen.getByTestId('perfil-nombre'), { target: { value: 'Ana María' } })
    fireEvent.click(screen.getByTestId('perfil-submit'))

    await waitFor(() => expect(perfilService.updatePerfil).toHaveBeenCalled())
    const sentBody = vi.mocked(perfilService.updatePerfil).mock.calls[0][0]
    expect(sentBody).not.toHaveProperty('id')
    expect(sentBody).not.toHaveProperty('cuil')
    expect(sentBody).not.toHaveProperty('legajo')
    expect(sentBody.nombre).toBe('Ana María')
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it('shows error toast on 409 email duplicado', async () => {
    const { toast } = await import('sonner')
    vi.mocked(perfilService.getPerfil).mockResolvedValue(samplePerfil)
    vi.mocked(perfilService.updatePerfil).mockRejectedValue({
      status: 409,
      detail: 'email ya usado en el tenant',
    })
    render(<PerfilPage />, { wrapper })

    await waitFor(() => expect(screen.getByDisplayValue('Ana')).toBeInTheDocument())
    fireEvent.change(screen.getByTestId('perfil-email'), { target: { value: 'dup@test.com' } })
    fireEvent.click(screen.getByTestId('perfil-submit'))

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('email ya usado en el tenant'),
    )
  })
})
