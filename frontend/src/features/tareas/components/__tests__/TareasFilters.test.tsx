/**
 * TareasFilters component tests.
 * Verifies: renders selects for materia and estado, UsuarioCombobox for docente,
 * onFilter emits correct values, empty options clear the filter.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TareasFilters from '../TareasFilters'
import type { MisEquiposItem } from '@/features/equipos/types'
import type { MiAsignacionRead } from '@/features/padron/services/misAsignacionesService'

vi.mock('@/features/equipos/services/equiposService')
vi.mock('@/features/padron/services/misAsignacionesService')

// Mock UsuarioCombobox to avoid hook complexity in this test
vi.mock('@/features/asignaciones/components/UsuarioCombobox', () => ({
  default: ({
    value,
    onChange,
  }: {
    value: string | null
    onChange: (id: string | null) => void
  }) => (
    <div data-testid="usuario-combobox">
      <button
        type="button"
        data-testid="combobox-select-user"
        onClick={() => onChange('docente-uuid-1')}
      >
        Seleccionar docente
      </button>
      {value && (
        <button type="button" data-testid="combobox-clear" onClick={() => onChange(null)}>
          Limpiar
        </button>
      )}
    </div>
  ),
}))

import * as equiposService from '@/features/equipos/services/equiposService'
import * as asignacionesService from '@/features/padron/services/misAsignacionesService'

const sampleEquipoItem: MisEquiposItem = {
  asignacion_id: 'asgn-1',
  usuario_id: 'docente-uuid-1',
  usuario_nombre: 'Carlos',
  usuario_apellidos: 'López',
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  materia_nombre: 'Matemáticas',
  carrera_nombre: 'Ingeniería',
  cohorte_nombre: '2024',
  rol: 'PROFESOR',
  desde: '2024-03-01',
  hasta: null,
  estado_vigencia: 'vigente',
  comisiones: [],
  responsable_id: null,
}

const sampleAsignacion: MiAsignacionRead = {
  materia_id: 'mat-2',
  materia_nombre: 'Historia',
  cohorte_id: 'coh-1',
  cohorte_nombre: '2024',
  rol: 'COORDINADOR',
  comisiones: [],
}

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(equiposService.listarMisEquipos).mockResolvedValue([sampleEquipoItem])
  vi.mocked(asignacionesService.getMisAsignaciones).mockResolvedValue([sampleAsignacion])
})

describe('TareasFilters — render', () => {
  it('renders the tareas-filters container', () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('tareas-filters')).toBeInTheDocument()
  })

  it('renders UsuarioCombobox for docente filter', () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('usuario-combobox')).toBeInTheDocument()
  })

  it('renders materia select with "Todas las materias" as default', async () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    const select = screen.getByTestId('filtro-materia')
    expect(select).toBeInTheDocument()
    expect(screen.getByText('Todas las materias')).toBeInTheDocument()
  })

  it('loads materia options from listarMisEquipos', async () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText('Matemáticas')).toBeInTheDocument()
    )
  })

  it('loads extra materia options from getMisAsignaciones (deduped)', async () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText('Historia')).toBeInTheDocument()
    )
  })

  it('renders estado select with "Todos los estados" as default', () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByText('Todos los estados')).toBeInTheDocument()
  })

  it('renders Filtrar and Limpiar buttons', () => {
    render(<TareasFilters onFilter={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByRole('button', { name: /Filtrar/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Limpiar/i })).toBeInTheDocument()
  })
})

describe('TareasFilters — onFilter emission', () => {
  it('emits asignado_a from combobox when Filtrar is clicked', async () => {
    const onFilter = vi.fn()
    render(<TareasFilters onFilter={onFilter} />, { wrapper: makeWrapper() })

    // Select a docente via the mocked combobox
    fireEvent.click(screen.getByTestId('combobox-select-user'))
    fireEvent.click(screen.getByRole('button', { name: /Filtrar/i }))

    expect(onFilter).toHaveBeenCalledWith(
      expect.objectContaining({ asignado_a: 'docente-uuid-1' }),
    )
  })

  it('emits materia_id when a materia is selected', async () => {
    const onFilter = vi.fn()
    render(<TareasFilters onFilter={onFilter} />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Matemáticas'))

    fireEvent.change(screen.getByTestId('filtro-materia'), { target: { value: 'mat-1' } })
    fireEvent.click(screen.getByRole('button', { name: /Filtrar/i }))

    expect(onFilter).toHaveBeenCalledWith(
      expect.objectContaining({ materia_id: 'mat-1' }),
    )
  })

  it('emits null for materia_id when "Todas las materias" is selected', async () => {
    const onFilter = vi.fn()
    render(<TareasFilters onFilter={onFilter} />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Matemáticas'))

    // Select a materia first, then go back to empty
    fireEvent.change(screen.getByTestId('filtro-materia'), { target: { value: 'mat-1' } })
    fireEvent.change(screen.getByTestId('filtro-materia'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /Filtrar/i }))

    expect(onFilter).toHaveBeenCalledWith(
      expect.objectContaining({ materia_id: null }),
    )
  })

  it('Limpiar resets all filters and calls onFilter with empty object', async () => {
    const onFilter = vi.fn()
    render(<TareasFilters onFilter={onFilter} />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Matemáticas'))

    // Set some filters
    fireEvent.click(screen.getByTestId('combobox-select-user'))
    fireEvent.change(screen.getByTestId('filtro-materia'), { target: { value: 'mat-1' } })

    // Clear — use getAllByRole and pick the last one (filter Limpiar, not combobox clear)
    const limpiarBtns = screen.getAllByRole('button', { name: /Limpiar/i })
    fireEvent.click(limpiarBtns[limpiarBtns.length - 1])

    expect(onFilter).toHaveBeenLastCalledWith({})
  })

  it('emits null for asignado_a when combobox is cleared before Filtrar', async () => {
    const onFilter = vi.fn()
    render(<TareasFilters onFilter={onFilter} />, { wrapper: makeWrapper() })

    // Select then clear
    fireEvent.click(screen.getByTestId('combobox-select-user'))
    fireEvent.click(screen.getByTestId('combobox-clear'))
    fireEvent.click(screen.getByRole('button', { name: /Filtrar/i }))

    expect(onFilter).toHaveBeenCalledWith(
      expect.objectContaining({ asignado_a: null }),
    )
  })
})
