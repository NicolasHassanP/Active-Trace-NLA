/**
 * AsignacionesTable component tests — UX fix: show usuario_nombre instead of raw UUID.
 *
 * RED → GREEN → TRIANGULATE
 * Tests:
 *   1. Shows full name when usuario_nombre and usuario_apellidos are present.
 *   2. Shows truncated UUID fallback when usuario_nombre is absent.
 *   3. Shows UUID fallback when nombre fields are null.
 *   4. Column header reads "Usuario" not "Usuario ID".
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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

describe('AsignacionesTable', () => {
  it('shows full name when usuario_nombre and usuario_apellidos are present', () => {
    const asignacion = makeAsignacion({
      usuario_nombre: 'Lucía',
      usuario_apellidos: 'Fernández',
    })
    render(
      <AsignacionesTable
        asignaciones={[asignacion]}
        onFilter={noop}
        onClear={noop}
        onEdit={noop}
        onDelete={noop}
        isDeleting={false}
      />,
    )
    expect(screen.getByText('Lucía Fernández')).toBeInTheDocument()
  })

  it('shows truncated UUID fallback when usuario_nombre is absent (undefined)', () => {
    const asignacion = makeAsignacion({
      usuario_nombre: undefined,
      usuario_apellidos: undefined,
    })
    render(
      <AsignacionesTable
        asignaciones={[asignacion]}
        onFilter={noop}
        onClear={noop}
        onEdit={noop}
        onDelete={noop}
        isDeleting={false}
      />,
    )
    // Falls back to sliced UUID
    expect(screen.getByText('e8844236…')).toBeInTheDocument()
  })

  it('shows truncated UUID fallback when nombre fields are null', () => {
    const asignacion = makeAsignacion({
      usuario_nombre: null,
      usuario_apellidos: null,
    })
    render(
      <AsignacionesTable
        asignaciones={[asignacion]}
        onFilter={noop}
        onClear={noop}
        onEdit={noop}
        onDelete={noop}
        isDeleting={false}
      />,
    )
    expect(screen.getByText('e8844236…')).toBeInTheDocument()
  })

  it('column header reads "Usuario" not "Usuario ID"', () => {
    render(
      <AsignacionesTable
        asignaciones={[makeAsignacion({ usuario_nombre: 'A', usuario_apellidos: 'B' })]}
        onFilter={noop}
        onClear={noop}
        onEdit={noop}
        onDelete={noop}
        isDeleting={false}
      />,
    )
    expect(screen.queryByText('Usuario ID')).not.toBeInTheDocument()
    expect(screen.getByText('Usuario')).toBeInTheDocument()
  })
})
