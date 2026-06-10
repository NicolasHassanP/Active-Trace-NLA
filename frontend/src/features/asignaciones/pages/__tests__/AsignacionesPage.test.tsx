/**
 * AsignacionesPage render tests — form + table render, happy-path create, edit, delete, error.
 * Service is mocked so no real network/auth is needed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AsignacionesPage from '../AsignacionesPage'
import * as asignacionService from '../../services/asignacionService'
import type { AsignacionRead } from '../../types'

vi.mock('../../services/asignacionService')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

const wrapper = ({ children }: { children: React.ReactNode }) =>
  createElement(
    QueryClientProvider,
    {
      client: new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
    },
    children,
  )

const sampleAsignacion: AsignacionRead = {
  id: 'asgn-1',
  usuario_id: 'user-uuid-1234-5678-abcd-ef0123456789',
  rol: 'PROFESOR',
  desde: '2026-03-01',
  hasta: null,
  materia_id: null,
  carrera_id: null,
  cohorte_id: null,
  comisiones: [],
  responsable_id: null,
  estado_vigencia: 'vigente',
  created_at: '2026-03-01T10:00:00',
  updated_at: '2026-03-01T10:00:00',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(asignacionService.listarAsignaciones).mockResolvedValue([sampleAsignacion])
})

describe('AsignacionesPage', () => {
  it('renders the create form and the table after load', async () => {
    render(<AsignacionesPage />, { wrapper })
    expect(screen.getByTestId('asignacion-form')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('asignaciones-table')).toBeInTheDocument())
  })

  it('shows empty state when no asignaciones are returned', async () => {
    vi.mocked(asignacionService.listarAsignaciones).mockResolvedValue([])
    render(<AsignacionesPage />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('asignaciones-empty')).toBeInTheDocument())
  })

  it('creates an asignacion and shows a success toast', async () => {
    const { toast } = await import('sonner')
    vi.mocked(asignacionService.crearAsignacion).mockResolvedValue(sampleAsignacion)
    render(<AsignacionesPage />, { wrapper })

    fireEvent.change(screen.getByTestId('asgn-usuario-id'), {
      target: { value: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11' },
    })
    fireEvent.change(screen.getByTestId('asgn-rol'), { target: { value: 'PROFESOR' } })
    fireEvent.change(screen.getByTestId('asgn-desde'), { target: { value: '2026-03-01' } })
    fireEvent.click(screen.getByTestId('asgn-submit'))

    await waitFor(() => expect(asignacionService.crearAsignacion).toHaveBeenCalled())
    const sentBody = vi.mocked(asignacionService.crearAsignacion).mock.calls[0][0]
    expect(sentBody.usuario_id).toBe('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11')
    expect(sentBody.rol).toBe('PROFESOR')
    expect(sentBody).not.toHaveProperty('tenant_id')
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it('shows an error toast when create fails', async () => {
    const { toast } = await import('sonner')
    vi.mocked(asignacionService.crearAsignacion).mockRejectedValue({
      status: 422,
      detail: 'Usuario no encontrado',
    })
    render(<AsignacionesPage />, { wrapper })

    fireEvent.change(screen.getByTestId('asgn-usuario-id'), {
      target: { value: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11' },
    })
    fireEvent.change(screen.getByTestId('asgn-desde'), { target: { value: '2026-03-01' } })
    fireEvent.click(screen.getByTestId('asgn-submit'))

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Usuario no encontrado'),
    )
  })

  it('shows error state when list query fails', async () => {
    vi.mocked(asignacionService.listarAsignaciones).mockRejectedValue({
      status: 403,
      detail: 'sin permiso',
    })
    render(<AsignacionesPage />, { wrapper })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('switches to edit mode when Editar is clicked on a row', async () => {
    render(<AsignacionesPage />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('asignaciones-table')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('btn-editar-asgn-1'))
    // In edit mode the form should NOT show the usuario_id field
    expect(screen.queryByTestId('asgn-usuario-id')).not.toBeInTheDocument()
    expect(screen.getByTestId('asgn-submit')).toHaveTextContent('Guardar cambios')
  })

  it('calls darBajaAsignacion and shows success toast when Dar baja is clicked', async () => {
    const { toast } = await import('sonner')
    vi.mocked(asignacionService.darBajaAsignacion).mockResolvedValue(undefined)
    render(<AsignacionesPage />, { wrapper })
    await waitFor(() => expect(screen.getByTestId('asignaciones-table')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('btn-baja-asgn-1'))
    await waitFor(() => expect(asignacionService.darBajaAsignacion).toHaveBeenCalledWith('asgn-1'))
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })
})
