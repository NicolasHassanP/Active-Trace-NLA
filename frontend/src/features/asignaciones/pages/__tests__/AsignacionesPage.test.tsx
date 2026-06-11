/**
 * AsignacionesPage render tests — form + table render, happy-path create, edit, delete, error.
 * Service is mocked so no real network/auth is needed.
 *
 * NOTE: usuario_id is now entered via UsuarioCombobox (not a raw UUID input).
 * Create-flow tests use the combobox: type query → select option → submit form.
 * buscarUsuariosAsignables is mocked to return a known user.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AsignacionesPage from '../AsignacionesPage'
import * as asignacionService from '../../services/asignacionService'
import type { AsignacionRead, UsuarioAsignable } from '../../types'

vi.mock('../../services/asignacionService')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

const makeWrapper = () => ({ children }: { children: React.ReactNode }) =>
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
  usuario_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
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

const sampleUsuario: UsuarioAsignable = {
  id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  nombre: 'Ana',
  apellidos: 'García',
  email: 'ana@test.com',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(asignacionService.listarAsignaciones).mockResolvedValue([sampleAsignacion])
  vi.mocked(asignacionService.buscarUsuariosAsignables).mockResolvedValue([sampleUsuario])
})

describe('AsignacionesPage', () => {
  it('renders the create form and the table after load', async () => {
    render(<AsignacionesPage />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('asignacion-form')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('asignaciones-table')).toBeInTheDocument())
  })

  it('shows empty state when no asignaciones are returned', async () => {
    vi.mocked(asignacionService.listarAsignaciones).mockResolvedValue([])
    render(<AsignacionesPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('asignaciones-empty')).toBeInTheDocument())
  })

  it('renders the combobox input in create mode', () => {
    render(<AsignacionesPage />, { wrapper: makeWrapper() })
    // The combobox replaces the raw UUID input
    expect(screen.getByTestId('usuario-combobox-input')).toBeInTheDocument()
    // Old UUID input is gone
    expect(screen.queryByTestId('asgn-usuario-id')).not.toBeInTheDocument()
  })

  it('creates an asignacion via combobox selection and shows a success toast', async () => {
    const { toast } = await import('sonner')
    vi.mocked(asignacionService.crearAsignacion).mockResolvedValue(sampleAsignacion)
    render(<AsignacionesPage />, { wrapper: makeWrapper() })

    // Type in the combobox to search
    const comboInput = screen.getByTestId('usuario-combobox-input')
    fireEvent.change(comboInput, { target: { value: 'ana' } })

    // Wait for dropdown with the mocked user option
    await waitFor(() => {
      expect(screen.queryByTestId(`usuario-option-${sampleUsuario.id}`)).toBeInTheDocument()
    })

    // Select the user
    fireEvent.mouseDown(screen.getByTestId(`usuario-option-${sampleUsuario.id}`))

    // Fill in other fields
    fireEvent.change(screen.getByTestId('asgn-rol'), { target: { value: 'PROFESOR' } })
    fireEvent.change(screen.getByTestId('asgn-desde'), { target: { value: '2026-03-01' } })
    fireEvent.click(screen.getByTestId('asgn-submit'))

    await waitFor(() => expect(asignacionService.crearAsignacion).toHaveBeenCalled())
    const sentBody = vi.mocked(asignacionService.crearAsignacion).mock.calls[0][0]
    expect(sentBody.usuario_id).toBe(sampleUsuario.id)
    expect(sentBody.rol).toBe('PROFESOR')
    expect(sentBody).not.toHaveProperty('tenant_id')
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it('shows error state when list query fails', async () => {
    vi.mocked(asignacionService.listarAsignaciones).mockRejectedValue({
      status: 403,
      detail: 'sin permiso',
    })
    render(<AsignacionesPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('switches to edit mode when Editar is clicked on a row', async () => {
    render(<AsignacionesPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('asignaciones-table')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('btn-editar-asgn-1'))
    // In edit mode the form should NOT show the combobox (usuario_id not editable)
    expect(screen.queryByTestId('usuario-combobox-input')).not.toBeInTheDocument()
    expect(screen.getByTestId('asgn-submit')).toHaveTextContent('Guardar cambios')
  })

  it('calls darBajaAsignacion and shows success toast when Dar baja is clicked', async () => {
    const { toast } = await import('sonner')
    vi.mocked(asignacionService.darBajaAsignacion).mockResolvedValue(undefined)
    render(<AsignacionesPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByTestId('asignaciones-table')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('btn-baja-asgn-1'))
    await waitFor(() => expect(asignacionService.darBajaAsignacion).toHaveBeenCalledWith('asgn-1'))
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })
})
