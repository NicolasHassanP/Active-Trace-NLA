/**
 * AsignacionMasivaForm render tests.
 *
 * Verifies:
 *   - materia and cohorte selects are rendered with option labels from the mocked lists
 *   - carrera field remains a plain input (no endpoint)
 *   - UsuarioMultiCombobox input is rendered (user search combobox)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import AsignacionMasivaForm from '../AsignacionMasivaForm'
import type { MateriaItem, CohorteItem } from '@/features/monitores/types'

// Mock the monitoresService to return controlled lists
vi.mock('@/features/monitores/services/monitoresService', () => ({
  listarTodasMaterias: vi.fn(),
  listarTodosCohortes: vi.fn(),
}))

// Mock the asignacionHooks used by UsuarioMultiCombobox
vi.mock('@/features/asignaciones/hooks/asignacionHooks', () => ({
  useBuscarUsuariosAsignables: vi.fn().mockReturnValue({
    data: [],
    isFetching: false,
    isLoading: false,
  }),
}))

// Mock useAsignacionMasiva to avoid network calls
vi.mock('../../hooks/equiposHooks', () => ({
  useAsignacionMasiva: vi.fn().mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
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
  { id: 'coh-2', carrera_id: 'car-1', nombre: 'Cohorte 2025', anio: 2025, estado: 'activo' },
]

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  mockMaterias.mockResolvedValue(sampleMaterias)
  mockCohortes.mockResolvedValue(sampleCohortes)
})

// ── render ──────────────────────────────────────────────────────────────────

describe('AsignacionMasivaForm — render', () => {
  it('renders the UsuarioMultiCombobox search input', () => {
    render(<AsignacionMasivaForm />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('usuario-multi-combobox-input')).toBeTruthy()
  })

  it('renders materia select with options by nombre', async () => {
    render(<AsignacionMasivaForm />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('masiva-materia-id')
      expect(select).toBeTruthy()
      // Option labels should be name, not UUID
      expect(select.textContent).toContain('Matemática I')
      expect(select.textContent).toContain('Física I')
    })
  })

  it('renders cohorte select with options by nombre', async () => {
    render(<AsignacionMasivaForm />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('masiva-cohorte-id')
      expect(select).toBeTruthy()
      expect(select.textContent).toContain('Cohorte 2024')
      expect(select.textContent).toContain('Cohorte 2025')
    })
  })

  it('renders carrera as a plain text input (no endpoint yet)', () => {
    render(<AsignacionMasivaForm />, { wrapper: makeWrapper() })
    const carreraInput = screen.getByTestId('masiva-carrera-id')
    // Should be an <input>, not a <select>
    expect(carreraInput.tagName.toLowerCase()).toBe('input')
  })

  it('materia options have correct values (UUIDs as option value)', async () => {
    render(<AsignacionMasivaForm />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('masiva-materia-id') as HTMLSelectElement
      const options = Array.from(select.options)
      const mat1Option = options.find((o) => o.value === 'mat-1')
      expect(mat1Option?.text).toBe('Matemática I')
    })
  })

  it('cohorte options have correct values (UUIDs as option value)', async () => {
    render(<AsignacionMasivaForm />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('masiva-cohorte-id') as HTMLSelectElement
      const options = Array.from(select.options)
      const coh1Option = options.find((o) => o.value === 'coh-1')
      expect(coh1Option?.text).toBe('Cohorte 2024')
    })
  })
})
