/**
 * Tests for admin-usuarios components: UsuariosTable and UsuarioForm.
 *
 * Key scenarios:
 *   - Table shows non-PII columns (nombre, apellidos, email, legajo, estado)
 *   - Table NEVER shows PII fields (dni, cuil, cbu, alias_cbu)
 *   - Form NEVER renders PII fields (dni, cuil, cbu, alias_cbu) — anti-PII test
 *   - Form renders only approved non-PII fields
 *   - Baja (delete) shows confirmation before calling onDelete
 *   - Edit populates form with existing data
 *   - 409 ConflictoEmail error displayed
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UsuariosTable from '../UsuariosTable'
import UsuarioForm from '../UsuarioForm'
import type { UsuarioRead } from '../../types'

const sampleUsuario: UsuarioRead = {
  id: 'usr-uuid-1',
  email: 'ana@test.com',
  nombre: 'Ana',
  apellidos: 'García',
  legajo: 'LEG001',
  estado: 'activo',
  asignaciones: [],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

const sampleUsuario2: UsuarioRead = {
  id: 'usr-uuid-2',
  email: 'pedro@test.com',
  nombre: 'Pedro',
  apellidos: 'López',
  legajo: null,
  estado: 'inactivo',
  asignaciones: [],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

// ── UsuariosTable ─────────────────────────────────────────────────────────────

describe('UsuariosTable — non-PII columns', () => {
  it('renders nombre, apellidos, email, estado columns', () => {
    render(
      <UsuariosTable
        usuarios={[sampleUsuario]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isDeleting={false}
      />
    )
    expect(screen.getByText('Ana')).toBeInTheDocument()
    expect(screen.getByText('García')).toBeInTheDocument()
    expect(screen.getByText('ana@test.com')).toBeInTheDocument()
  })

  it('shows empty state when no usuarios', () => {
    render(
      <UsuariosTable
        usuarios={[]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isDeleting={false}
      />
    )
    expect(screen.getByTestId('usuarios-empty')).toBeInTheDocument()
  })

  it('table NEVER has a column header for dni', () => {
    render(
      <UsuariosTable
        usuarios={[sampleUsuario]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isDeleting={false}
      />
    )
    const headers = screen.getAllByRole('columnheader').map(h => h.textContent?.toLowerCase() ?? '')
    expect(headers.some(h => h.includes('dni'))).toBe(false)
    expect(headers.some(h => h.includes('cuil'))).toBe(false)
    expect(headers.some(h => h.includes('cbu'))).toBe(false)
  })

  it('calls onDelete after window.confirm returns true', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const onDelete = vi.fn()
    render(
      <UsuariosTable
        usuarios={[sampleUsuario]}
        onEdit={vi.fn()}
        onDelete={onDelete}
        isDeleting={false}
      />
    )
    fireEvent.click(screen.getByTestId(`btn-baja-${sampleUsuario.id}`))
    expect(confirmSpy).toHaveBeenCalled()
    expect(onDelete).toHaveBeenCalledWith(sampleUsuario.id)
    confirmSpy.mockRestore()
  })

  it('does NOT call onDelete when window.confirm returns false', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const onDelete = vi.fn()
    render(
      <UsuariosTable
        usuarios={[sampleUsuario]}
        onEdit={vi.fn()}
        onDelete={onDelete}
        isDeleting={false}
      />
    )
    fireEvent.click(screen.getByTestId(`btn-baja-${sampleUsuario.id}`))
    expect(confirmSpy).toHaveBeenCalled()
    expect(onDelete).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('calls onEdit with the usuario when edit button clicked', () => {
    const onEdit = vi.fn()
    render(
      <UsuariosTable
        usuarios={[sampleUsuario]}
        onEdit={onEdit}
        onDelete={vi.fn()}
        isDeleting={false}
      />
    )
    fireEvent.click(screen.getByTestId(`btn-editar-${sampleUsuario.id}`))
    expect(onEdit).toHaveBeenCalledWith(sampleUsuario)
  })

  it('renders multiple usuarios', () => {
    render(
      <UsuariosTable
        usuarios={[sampleUsuario, sampleUsuario2]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        isDeleting={false}
      />
    )
    expect(screen.getByText('Ana')).toBeInTheDocument()
    expect(screen.getByText('Pedro')).toBeInTheDocument()
  })
})

// ── UsuarioForm — anti-PII tests ──────────────────────────────────────────────

describe('UsuarioForm — anti-PII (form NEVER renders PII fields)', () => {
  it('does NOT render a field for dni', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    // No input with name/id/label containing "dni"
    expect(screen.queryByLabelText(/dni/i)).toBeNull()
    expect(screen.queryByTestId('usuario-dni')).toBeNull()
  })

  it('does NOT render a field for cuil', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.queryByLabelText(/cuil/i)).toBeNull()
    expect(screen.queryByTestId('usuario-cuil')).toBeNull()
  })

  it('does NOT render a field for cbu', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.queryByLabelText(/cbu/i)).toBeNull()
    expect(screen.queryByTestId('usuario-cbu')).toBeNull()
  })

  it('does NOT render a field for alias_cbu', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.queryByLabelText(/alias/i)).toBeNull()
    expect(screen.queryByTestId('usuario-alias-cbu')).toBeNull()
  })

  it('does NOT render a field for banco', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.queryByLabelText(/banco/i)).toBeNull()
    expect(screen.queryByTestId('usuario-banco')).toBeNull()
  })

  it('does NOT render a field for facturador', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.queryByLabelText(/facturador/i)).toBeNull()
    expect(screen.queryByTestId('usuario-facturador')).toBeNull()
  })
})

// ── UsuarioForm — approved non-PII fields ────────────────────────────────────

describe('UsuarioForm — approved fields', () => {
  it('renders email, nombre, apellidos, legajo, estado fields', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.getByTestId('usuario-email')).toBeInTheDocument()
    expect(screen.getByTestId('usuario-nombre')).toBeInTheDocument()
    expect(screen.getByTestId('usuario-apellidos')).toBeInTheDocument()
    expect(screen.getByTestId('usuario-legajo')).toBeInTheDocument()
    expect(screen.getByTestId('usuario-estado')).toBeInTheDocument()
  })

  it('renders in create mode by default (no initialValues)', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.getByTestId('usuario-submit')).toHaveTextContent('Crear usuario')
  })

  it('renders in edit mode when initialValues provided', () => {
    render(
      <UsuarioForm
        initialValues={sampleUsuario}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />
    )
    expect(screen.getByTestId('usuario-submit')).toHaveTextContent('Guardar cambios')
    const emailInput = screen.getByTestId('usuario-email') as HTMLInputElement
    expect(emailInput.value).toBe('ana@test.com')
  })

  it('shows domain error message when errorMessage prop is set', () => {
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
        errorMessage="Email ya registrado (ConflictoEmail)"
      />
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Email ya registrado')
  })

  it('calls onCancel when cancel button clicked', () => {
    const onCancel = vi.fn()
    render(
      <UsuarioForm
        onSubmit={vi.fn()}
        onCancel={onCancel}
        isSubmitting={false}
      />
    )
    fireEvent.click(screen.getByText('Cancelar'))
    expect(onCancel).toHaveBeenCalled()
  })
})
