/**
 * AsignacionForm render tests.
 *
 * Verifies:
 *   - materia and cohorte selects render with option labels from mocked lists
 *   - carrera field remains a plain input (no endpoint)
 *   - UsuarioCombobox is shown in create mode
 *   - UsuarioCombobox is hidden in edit mode
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import AsignacionForm from '../AsignacionForm'
import type { MateriaItem, CohorteItem } from '@/features/monitores/types'
import type { AsignacionFormValues } from '../AsignacionForm'

// Mock the monitoresService
vi.mock('@/features/monitores/services/monitoresService', () => ({
  listarTodasMaterias: vi.fn(),
  listarTodosCohortes: vi.fn(),
}))

// Mock asignacionHooks used by UsuarioCombobox
vi.mock('../hooks/asignacionHooks', () => ({
  useBuscarUsuariosAsignables: vi.fn().mockReturnValue({
    data: [],
    isFetching: false,
    isLoading: false,
  }),
}))

import { listarTodasMaterias, listarTodosCohortes } from '@/features/monitores/services/monitoresService'

const mockMaterias = vi.mocked(listarTodasMaterias)
const mockCohortes = vi.mocked(listarTodosCohortes)

const sampleMaterias: MateriaItem[] = [
  { id: 'mat-1', codigo: 'MAT101', nombre: 'Matemática I', estado: 'activo' },
  { id: 'mat-2', codigo: 'FIS101', nombre: 'Física I', estado: 'activo' },
]

const sampleCohortes: CohorteItem[] = [
  { id: 'coh-1', carrera_id: 'car-1', nombre: 'Cohorte 2024', anio: 2024, estado: 'activo' },
]

const sampleInitialValues: AsignacionFormValues = {
  usuario_id: 'user-uuid-123',
  rol: 'PROFESOR',
  desde: '2024-01-01',
  hasta: null,
  materia_id: 'mat-1',
  carrera_id: null,
  cohorte_id: null,
  responsable_id: null,
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  mockMaterias.mockResolvedValue(sampleMaterias)
  mockCohortes.mockResolvedValue(sampleCohortes)
})

// ── create mode ─────────────────────────────────────────────────────────────

describe('AsignacionForm — create mode', () => {
  it('renders UsuarioCombobox in create mode', () => {
    render(
      <AsignacionForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByTestId('usuario-combobox')).toBeTruthy()
  })

  it('renders materia select with options by nombre', async () => {
    render(
      <AsignacionForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )

    await waitFor(() => {
      const select = screen.getByTestId('asgn-materia-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Matemática I')
      expect(select.textContent).toContain('Física I')
    })
  })

  it('renders cohorte select with options by nombre', async () => {
    render(
      <AsignacionForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )

    await waitFor(() => {
      const select = screen.getByTestId('asgn-cohorte-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Cohorte 2024')
    })
  })

  it('renders carrera as a plain text input (no endpoint yet)', () => {
    render(
      <AsignacionForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )
    const carreraInput = screen.getByTestId('asgn-carrera-id')
    expect(carreraInput.tagName.toLowerCase()).toBe('input')
  })

  it('materia option values are UUIDs, labels are names', async () => {
    render(
      <AsignacionForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )

    await waitFor(() => {
      const select = screen.getByTestId('asgn-materia-id') as HTMLSelectElement
      const mat1 = Array.from(select.options).find((o) => o.value === 'mat-1')
      expect(mat1?.text).toBe('Matemática I')
    })
  })
})

// ── edit mode ────────────────────────────────────────────────────────────────

describe('AsignacionForm — edit mode', () => {
  it('does NOT render UsuarioCombobox in edit mode', () => {
    render(
      <AsignacionForm
        initialValues={sampleInitialValues}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />,
      { wrapper: makeWrapper() },
    )
    expect(screen.queryByTestId('usuario-combobox')).toBeNull()
  })

  it('still renders materia and cohorte selects in edit mode', async () => {
    render(
      <AsignacionForm
        initialValues={sampleInitialValues}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />,
      { wrapper: makeWrapper() },
    )

    await waitFor(() => {
      expect(screen.getByTestId('asgn-materia-id').tagName.toLowerCase()).toBe('select')
      expect(screen.getByTestId('asgn-cohorte-id').tagName.toLowerCase()).toBe('select')
    })
  })
})
