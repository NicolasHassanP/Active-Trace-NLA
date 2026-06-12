/**
 * Tests for EstructuraTable components — CarrerasTable, MateriasTable, CohortesTable.
 * Covers: renders rows, filters client-side, edit/delete callbacks, empty state.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CarrerasTable from '../CarrerasTable'
import MateriasTable from '../MateriasTable'
import CohortesTable from '../CohortesTable'
import type { CarreraRead, MateriaRead, CohorteRead } from '../../types'

const carreras: CarreraRead[] = [
  { id: 'car-1', codigo: 'ING', nombre: 'Ingeniería', estado: 'activa', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
  { id: 'car-2', codigo: 'MED', nombre: 'Medicina', estado: 'inactiva', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
]

const materias: MateriaRead[] = [
  { id: 'mat-1', codigo: 'MAT1', nombre: 'Matemática I', estado: 'activa', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
  { id: 'mat-2', codigo: 'FIS1', nombre: 'Física I', estado: 'inactiva', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
]

const cohortes: CohorteRead[] = [
  { id: 'coh-1', carrera_id: 'car-1', nombre: '2026', anio: 2026, vig_desde: '2026-03-01', vig_hasta: null, estado: 'activa', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
  { id: 'coh-2', carrera_id: 'car-2', nombre: '2025', anio: 2025, vig_desde: '2025-03-01', vig_hasta: '2025-12-31', estado: 'inactiva', created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
]

// ── CarrerasTable ─────────────────────────────────────────────────────────────

describe('CarrerasTable', () => {
  it('renders all carrera rows', () => {
    render(<CarrerasTable carreras={carreras} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    expect(screen.getByText('Ingeniería')).toBeInTheDocument()
    expect(screen.getByText('Medicina')).toBeInTheDocument()
  })

  it('shows empty state when no carreras', () => {
    render(<CarrerasTable carreras={[]} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    expect(screen.getByTestId('carreras-empty')).toBeInTheDocument()
  })

  it('calls onEdit with the correct carrera', () => {
    const onEdit = vi.fn()
    render(<CarrerasTable carreras={carreras} onEdit={onEdit} onDelete={vi.fn()} isDeleting={false} />)
    fireEvent.click(screen.getByTestId('btn-editar-car-1'))
    expect(onEdit).toHaveBeenCalledWith(carreras[0])
  })

  it('calls onDelete with the correct id', () => {
    const onDelete = vi.fn()
    render(<CarrerasTable carreras={carreras} onEdit={vi.fn()} onDelete={onDelete} isDeleting={false} />)
    fireEvent.click(screen.getByTestId('btn-baja-car-1'))
    expect(onDelete).toHaveBeenCalledWith('car-1')
  })

  it('filters by nombre substring', () => {
    render(<CarrerasTable carreras={carreras} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    const input = screen.getByPlaceholderText(/nombre/i)
    fireEvent.change(input, { target: { value: 'Inge' } })
    expect(screen.getByText('Ingeniería')).toBeInTheDocument()
    expect(screen.queryByText('Medicina')).not.toBeInTheDocument()
  })

  it('disables baja button when isDeleting is true', () => {
    render(<CarrerasTable carreras={carreras} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={true} />)
    const btn = screen.getByTestId('btn-baja-car-1') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })
})

// ── MateriasTable ─────────────────────────────────────────────────────────────

describe('MateriasTable', () => {
  it('renders all materia rows', () => {
    render(<MateriasTable materias={materias} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    expect(screen.getByText('Matemática I')).toBeInTheDocument()
    expect(screen.getByText('Física I')).toBeInTheDocument()
  })

  it('shows empty state when no materias', () => {
    render(<MateriasTable materias={[]} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    expect(screen.getByTestId('materias-empty')).toBeInTheDocument()
  })

  it('calls onEdit with correct materia', () => {
    const onEdit = vi.fn()
    render(<MateriasTable materias={materias} onEdit={onEdit} onDelete={vi.fn()} isDeleting={false} />)
    fireEvent.click(screen.getByTestId('btn-editar-mat-1'))
    expect(onEdit).toHaveBeenCalledWith(materias[0])
  })

  it('filters by nombre substring', () => {
    render(<MateriasTable materias={materias} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    const input = screen.getByPlaceholderText(/nombre/i)
    fireEvent.change(input, { target: { value: 'Mate' } })
    expect(screen.getByText('Matemática I')).toBeInTheDocument()
    expect(screen.queryByText('Física I')).not.toBeInTheDocument()
  })
})

// ── CohortesTable ─────────────────────────────────────────────────────────────

describe('CohortesTable', () => {
  it('renders all cohorte rows', () => {
    render(<CohortesTable cohortes={cohortes} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    // nombre '2026' and anio 2026 both appear — use getAllByText
    expect(screen.getAllByText('2026').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2025').length).toBeGreaterThan(0)
  })

  it('shows empty state when no cohortes', () => {
    render(<CohortesTable cohortes={[]} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    expect(screen.getByTestId('cohortes-empty')).toBeInTheDocument()
  })

  it('calls onEdit with correct cohorte', () => {
    const onEdit = vi.fn()
    render(<CohortesTable cohortes={cohortes} onEdit={onEdit} onDelete={vi.fn()} isDeleting={false} />)
    fireEvent.click(screen.getByTestId('btn-editar-coh-1'))
    expect(onEdit).toHaveBeenCalledWith(cohortes[0])
  })

  it('shows — for vig_hasta null (cohorte abierta)', () => {
    render(<CohortesTable cohortes={cohortes} onEdit={vi.fn()} onDelete={vi.fn()} isDeleting={false} />)
    // First cohorte has vig_hasta null → should show '—'
    const cells = screen.getAllByText('—')
    expect(cells.length).toBeGreaterThan(0)
  })
})
