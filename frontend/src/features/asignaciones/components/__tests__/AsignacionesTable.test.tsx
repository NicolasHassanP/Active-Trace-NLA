/**
 * AsignacionesTable component tests.
 * Covers: display (name, UUID fallback, columns), client-side filtering (all filters).
 *
 * RED → GREEN → TRIANGULATE
 * Display tests (1-7):
 *   1. Shows full name when usuario_nombre and usuario_apellidos are present.
 *   2. Shows truncated UUID fallback when usuario_nombre is absent.
 *   3. Shows UUID fallback when nombre fields are null.
 *   4. Column header reads "Usuario" not "Usuario ID".
 *   5. Shows materia_nombre and cohorte_nombre column headers.
 *   6. Renders materia_nombre and cohorte_nombre when present.
 *   7. Shows "—" dash when materia_nombre/cohorte_nombre are null/undefined.
 *
 * Client-side filter tests (8-14):
 *   8.  Usuario filter — substring match (case-insensitive).
 *   9.  Usuario filter — no match shows empty state.
 *  10.  Rol filter — exact match hides non-matching rows.
 *  11.  Materia filter — exact match.
 *  12.  Cohorte filter — exact match.
 *  13.  Vigencia filter — exact match.
 *  14.  Rango Desde/Hasta — range over the "desde" column.
 *  15.  Limpiar filtros resets all filters and shows all rows.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AsignacionesTable from '../AsignacionesTable'
import type { AsignacionRead } from '../../types'

// Minimal stubs for callbacks — not under test here.
const noop = vi.fn()

function makeAsignacion(overrides: Partial<AsignacionRead> = {}): AsignacionRead {
  return {
    id: 'asgn-abc',
    usuario_id: 'e8844236-0000-0000-0000-000000000000',
    rol: 'PROFESOR',
    desde: '2026-01-01',
    hasta: null,
    materia_id: null,
    carrera_id: null,
    cohorte_id: null,
    comisiones: [],
    responsable_id: null,
    estado_vigencia: 'vigente',
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
    ...overrides,
  }
}

function renderTable(asignaciones: AsignacionRead[]) {
  return render(
    <AsignacionesTable
      asignaciones={asignaciones}
      onEdit={noop}
      onDelete={noop}
      isDeleting={false}
    />,
  )
}

describe('AsignacionesTable — display', () => {
  it('shows full name when usuario_nombre and usuario_apellidos are present', () => {
    renderTable([makeAsignacion({ usuario_nombre: 'Lucía', usuario_apellidos: 'Fernández' })])
    expect(screen.getByText('Lucía Fernández')).toBeInTheDocument()
  })

  it('shows truncated UUID fallback when usuario_nombre is absent (undefined)', () => {
    renderTable([makeAsignacion({ usuario_nombre: undefined, usuario_apellidos: undefined })])
    expect(screen.getByText('e8844236…')).toBeInTheDocument()
  })

  it('shows truncated UUID fallback when nombre fields are null', () => {
    renderTable([makeAsignacion({ usuario_nombre: null, usuario_apellidos: null })])
    expect(screen.getByText('e8844236…')).toBeInTheDocument()
  })

  it('column header reads "Usuario" not "Usuario ID"', () => {
    renderTable([makeAsignacion({ usuario_nombre: 'A', usuario_apellidos: 'B' })])
    expect(screen.queryByText('Usuario ID')).not.toBeInTheDocument()
    // "Usuario" appears as both filter label and column header — check column header specifically
    expect(screen.getByRole('columnheader', { name: /^usuario$/i })).toBeInTheDocument()
  })

  it('shows "Materia" and "Cohorte" column headers', () => {
    renderTable([makeAsignacion()])
    // "Materia"/"Cohorte" appear as filter labels and column headers — check headers specifically
    expect(screen.getByRole('columnheader', { name: /^materia$/i })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /^cohorte$/i })).toBeInTheDocument()
  })

  it('renders materia_nombre and cohorte_nombre when present', () => {
    renderTable([makeAsignacion({ materia_nombre: 'Álgebra I', cohorte_nombre: '2024-A' })])
    // Values appear in both dropdown options and table cells — check cells specifically
    expect(screen.getByRole('cell', { name: 'Álgebra I' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2024-A' })).toBeInTheDocument()
  })

  it('shows "—" dash when materia_nombre and cohorte_nombre are null', () => {
    renderTable([makeAsignacion({ materia_nombre: null, cohorte_nombre: null })])
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })
})

describe('AsignacionesTable — client-side filtering', () => {
  const luciaRowValid = makeAsignacion({
    id: 'asgn-1',
    usuario_nombre: 'Lucía',
    usuario_apellidos: 'Fernández',
    rol: 'TUTOR',
    materia_nombre: 'Álgebra I',
    cohorte_nombre: '2024-A',
    estado_vigencia: 'vigente',
    desde: '2026-03-01',
  })
  const carlosRow = makeAsignacion({
    id: 'asgn-2',
    usuario_nombre: 'Carlos',
    usuario_apellidos: 'López',
    rol: 'PROFESOR',
    materia_nombre: 'Cálculo II',
    cohorte_nombre: '2023-B',
    estado_vigencia: 'vencida',
    desde: '2025-01-01',
  })

  it('8. Usuario filter — substring match (case-insensitive) keeps matching row', () => {
    renderTable([luciaRowValid, carlosRow])
    fireEvent.change(screen.getByTestId('filtro-usuario'), { target: { value: 'lucía' } })
    expect(screen.getByText('Lucía Fernández')).toBeInTheDocument()
    expect(screen.queryByText('Carlos López')).not.toBeInTheDocument()
  })

  it('9. Usuario filter — no match shows empty state', () => {
    renderTable([luciaRowValid, carlosRow])
    fireEvent.change(screen.getByTestId('filtro-usuario'), { target: { value: 'xyz999' } })
    expect(screen.getByTestId('asignaciones-empty')).toBeInTheDocument()
  })

  it('10. Rol filter — exact match hides non-matching rows', () => {
    renderTable([luciaRowValid, carlosRow])
    fireEvent.change(screen.getByTestId('filtro-rol'), { target: { value: 'PROFESOR' } })
    expect(screen.queryByText('Lucía Fernández')).not.toBeInTheDocument()
    expect(screen.getByText('Carlos López')).toBeInTheDocument()
  })

  it('11. Materia filter — exact match', () => {
    renderTable([luciaRowValid, carlosRow])
    fireEvent.change(screen.getByTestId('filtro-materia'), { target: { value: 'Álgebra I' } })
    expect(screen.getByText('Lucía Fernández')).toBeInTheDocument()
    expect(screen.queryByText('Carlos López')).not.toBeInTheDocument()
  })

  it('12. Cohorte filter — exact match', () => {
    renderTable([luciaRowValid, carlosRow])
    fireEvent.change(screen.getByTestId('filtro-cohorte'), { target: { value: '2023-B' } })
    expect(screen.queryByText('Lucía Fernández')).not.toBeInTheDocument()
    expect(screen.getByText('Carlos López')).toBeInTheDocument()
  })

  it('13. Vigencia filter — exact match', () => {
    renderTable([luciaRowValid, carlosRow])
    fireEvent.change(screen.getByTestId('filtro-vigencia'), { target: { value: 'vencida' } })
    expect(screen.queryByText('Lucía Fernández')).not.toBeInTheDocument()
    expect(screen.getByText('Carlos López')).toBeInTheDocument()
  })

  it('14. Rango Desde — filters rows by desde >= value', () => {
    renderTable([luciaRowValid, carlosRow])
    // luciaRow.desde = 2026-03-01, carlosRow.desde = 2025-01-01
    // Filter desde = 2026-01-01 → only lucía passes
    fireEvent.change(screen.getByTestId('filtro-desde'), { target: { value: '2026-01-01' } })
    expect(screen.getByText('Lucía Fernández')).toBeInTheDocument()
    expect(screen.queryByText('Carlos López')).not.toBeInTheDocument()
  })

  it('14b. Rango Hasta — filters rows by desde <= value', () => {
    renderTable([luciaRowValid, carlosRow])
    // Filter hasta = 2025-12-31 → only carlos passes (desde 2025-01-01 ≤ 2025-12-31)
    fireEvent.change(screen.getByTestId('filtro-hasta'), { target: { value: '2025-12-31' } })
    expect(screen.queryByText('Lucía Fernández')).not.toBeInTheDocument()
    expect(screen.getByText('Carlos López')).toBeInTheDocument()
  })

  it('15. Limpiar filtros resets all filters and shows all rows', () => {
    renderTable([luciaRowValid, carlosRow])
    // Apply a filter first
    fireEvent.change(screen.getByTestId('filtro-usuario'), { target: { value: 'carlos' } })
    expect(screen.queryByText('Lucía Fernández')).not.toBeInTheDocument()
    // Clear
    fireEvent.click(screen.getByRole('button', { name: /limpiar filtros/i }))
    expect(screen.getByText('Lucía Fernández')).toBeInTheDocument()
    expect(screen.getByText('Carlos López')).toBeInTheDocument()
  })
})
