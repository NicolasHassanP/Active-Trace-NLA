/**
 * GuardiasPage render tests — form + table render, happy-path registration, error toast.
 * Service + equipos hook are mocked so no real network/auth is needed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GuardiasPage from '../GuardiasPage'
import * as guardiaService from '../../services/guardiaService'
import * as equiposHooks from '@/features/equipos/hooks/equiposHooks'
import type { GuardiaRead } from '../../types'
import type { MisEquiposItem } from '@/features/equipos/types'

vi.mock('../../services/guardiaService')
vi.mock('@/features/equipos/hooks/equiposHooks')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

const wrapper = ({ children }: { children: React.ReactNode }) =>
  createElement(QueryClientProvider, {
    client: new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }),
  }, children)

const sampleGuardia: GuardiaRead = {
  id: 'g-1',
  asignacion_id: 'a-1',
  materia_id: 'm-1',
  carrera_id: 'c-1',
  cohorte_id: 'co-1',
  dia: 'Lunes',
  horario: '10:00-12:00',
  estado: 'Pendiente',
  comentarios: 'Aula 5',
  creada_at: '2026-06-01T10:00:00',
}

const asignacion: MisEquiposItem = {
  asignacion_id: 'a-1',
  usuario_id: 'u-1',
  usuario_nombre: 'Ana',
  usuario_apellidos: 'Gómez',
  materia_id: 'm-1',
  carrera_id: 'c-1',
  cohorte_id: 'co-1',
  materia_nombre: 'Álgebra',
  carrera_nombre: 'Ingeniería',
  cohorte_nombre: '2026',
  rol: 'PROFESOR',
  desde: '2026-01-01',
  hasta: null,
  estado_vigencia: 'vigente',
  comisiones: [],
  responsable_id: null,
}

type EquipoQueryResult = ReturnType<typeof equiposHooks.useMisEquipos>

function mockMisEquipos(data: MisEquiposItem[]) {
  vi.mocked(equiposHooks.useMisEquipos).mockReturnValue({
    data,
    isLoading: false,
    isError: false,
  } as EquipoQueryResult)
}

beforeEach(() => {
  vi.clearAllMocks()
  mockMisEquipos([asignacion])
  vi.mocked(guardiaService.listarGuardias).mockResolvedValue([sampleGuardia])
})

describe('GuardiasPage', () => {
  it('renders the registration form and the guardias table', async () => {
    render(<GuardiasPage />, { wrapper })
    expect(screen.getByTestId('registrar-guardia-form')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('guardias-table')).toBeInTheDocument())
  })

  it('lists the materia/carrera/cohorte option from the user assignments', () => {
    render(<GuardiasPage />, { wrapper })
    expect(screen.getByText(/Álgebra · Ingeniería · 2026/)).toBeInTheDocument()
  })

  it('registers a guardia and shows a success toast', async () => {
    const { toast } = await import('sonner')
    vi.mocked(guardiaService.registrarGuardia).mockResolvedValue(sampleGuardia)
    render(<GuardiasPage />, { wrapper })

    fireEvent.change(screen.getByTestId('guardia-tripleta'), {
      target: { value: 'm-1|c-1|co-1' },
    })
    fireEvent.change(screen.getByTestId('guardia-horario'), { target: { value: '10:00-12:00' } })
    fireEvent.click(screen.getByTestId('guardia-submit'))

    await waitFor(() => expect(guardiaService.registrarGuardia).toHaveBeenCalled())
    const sentBody = vi.mocked(guardiaService.registrarGuardia).mock.calls[0][0]
    expect(sentBody.materia_id).toBe('m-1')
    expect(sentBody.carrera_id).toBe('c-1')
    expect(sentBody.cohorte_id).toBe('co-1')
    expect(sentBody).not.toHaveProperty('asignacion_id')
    expect(sentBody).not.toHaveProperty('tenant_id')
    await waitFor(() => expect(toast.success).toHaveBeenCalled())
  })

  it('shows an error toast when registration fails', async () => {
    const { toast } = await import('sonner')
    vi.mocked(guardiaService.registrarGuardia).mockRejectedValue({
      status: 422,
      detail: 'horario inválido',
    })
    render(<GuardiasPage />, { wrapper })

    fireEvent.change(screen.getByTestId('guardia-tripleta'), {
      target: { value: 'm-1|c-1|co-1' },
    })
    fireEvent.change(screen.getByTestId('guardia-horario'), { target: { value: 'bad' } })
    fireEvent.click(screen.getByTestId('guardia-submit'))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('horario inválido'))
  })

  it('shows the guardias error state when the list query fails', async () => {
    vi.mocked(guardiaService.listarGuardias).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    render(<GuardiasPage />, { wrapper })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
