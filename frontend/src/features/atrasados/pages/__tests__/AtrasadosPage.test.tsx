/**
 * AtrasadosPage render tests — covers table, empty state, selection, routing.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AtrasadosPage from '../AtrasadosPage'
import * as service from '../../services/atrasadosService'
import type { AlumnoAtrasado } from '../../types'

vi.mock('../../services/atrasadosService')

const wrapper =
  (route = '/materias/m1/cohortes/c1/atrasados') =>
  ({ children }: { children: React.ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client: new QueryClient({ defaultOptions: { queries: { retry: false } } }) },
      createElement(
        MemoryRouter,
        { initialEntries: [route] },
        createElement(
          Routes,
          null,
          createElement(Route, {
            path: '/materias/:materiaId/cohortes/:cohorteId/atrasados',
            element: children,
          }),
        ),
      ),
    )

const mockAlumnos: AlumnoAtrasado[] = [
  {
    alumno_id: 'a1', nombre: 'Ana', apellidos: 'Paz', email: 'ana@test.com',
    actividades_faltantes: ['TP1'], actividades_no_aprobadas: [], estado: 'atrasado',
  },
  {
    alumno_id: 'a2', nombre: 'Luis', apellidos: 'Vera', email: 'luis@test.com',
    actividades_faltantes: [], actividades_no_aprobadas: ['Parcial1'], estado: 'atrasado',
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(service.reporteMateria).mockResolvedValue({
    materia_id: 'm1', cohorte_id: 'c1',
    total_alumnos: 2, total_atrasados: 2, tasa_aprobacion: 0, sin_datos: false,
  })
})

describe('AtrasadosPage', () => {
  it('shows student rows after data loads', async () => {
    vi.mocked(service.listarAtrasados).mockResolvedValue(mockAlumnos)
    render(<AtrasadosPage />, { wrapper: wrapper() })
    await waitFor(() => expect(screen.getByText('Paz, Ana')).toBeInTheDocument())
    expect(screen.getByText('Vera, Luis')).toBeInTheDocument()
  })

  it('shows empty state when list is empty', async () => {
    vi.mocked(service.listarAtrasados).mockResolvedValue([])
    render(<AtrasadosPage />, { wrapper: wrapper() })
    await waitFor(() => expect(screen.getByTestId('atrasados-empty')).toBeInTheDocument())
  })

  it('comunicar button is disabled with no selection', async () => {
    vi.mocked(service.listarAtrasados).mockResolvedValue(mockAlumnos)
    render(<AtrasadosPage />, { wrapper: wrapper() })
    await waitFor(() => expect(screen.getByText('Paz, Ana')).toBeInTheDocument())
    expect(screen.getByTestId('comunicar-btn')).toBeDisabled()
  })

  it('comunicar button is enabled after selecting an alumno', async () => {
    vi.mocked(service.listarAtrasados).mockResolvedValue(mockAlumnos)
    render(<AtrasadosPage />, { wrapper: wrapper() })
    await waitFor(() => expect(screen.getByTestId('select-a1')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('select-a1'))
    expect(screen.getByTestId('comunicar-btn')).not.toBeDisabled()
  })

  it('shows error message when API call fails', async () => {
    vi.mocked(service.listarAtrasados).mockRejectedValue({ status: 403, detail: 'sin permiso' })
    render(<AtrasadosPage />, { wrapper: wrapper() })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
