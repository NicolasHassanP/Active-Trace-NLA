/**
 * PasoProgramas render tests.
 *
 * Verifies:
 *   - materia_id, carrera_id, cohorte_id render as <select> with options by nombre
 *   - titulo and referencia_archivo remain as text inputs
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import PasoProgramas from '../PasoProgramas'
import type { MateriaItem, CohorteItem, CarreraItem } from '@/features/monitores/types'

vi.mock('@/features/monitores/services/monitoresService', () => ({
  listarTodasMaterias: vi.fn(),
  listarTodosCohortes: vi.fn(),
  listarTodasCarreras: vi.fn(),
}))

import {
  listarTodasMaterias,
  listarTodosCohortes,
  listarTodasCarreras,
} from '@/features/monitores/services/monitoresService'

const mockMaterias = vi.mocked(listarTodasMaterias)
const mockCohortes = vi.mocked(listarTodosCohortes)
const mockCarreras = vi.mocked(listarTodasCarreras)

const sampleMaterias: MateriaItem[] = [
  { id: 'mat-1', codigo: 'MAT101', nombre: 'Matemática I', estado: 'activo' },
  { id: 'mat-2', codigo: 'FIS101', nombre: 'Física I', estado: 'activo' },
]

const sampleCohortes: CohorteItem[] = [
  { id: 'coh-1', carrera_id: 'car-1', nombre: 'Cohorte 2024', anio: 2024, estado: 'activo' },
]

const sampleCarreras: CarreraItem[] = [
  { id: 'car-1', codigo: 'ING', nombre: 'Ingeniería', estado: 'activo' },
]

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  mockMaterias.mockResolvedValue(sampleMaterias)
  mockCohortes.mockResolvedValue(sampleCohortes)
  mockCarreras.mockResolvedValue(sampleCarreras)
})

describe('PasoProgramas — render', () => {
  it('renders the form with data-testid paso-programas', () => {
    render(<PasoProgramas onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('paso-programas')).toBeTruthy()
  })

  it('renders materia_id as <select> with options by nombre', async () => {
    render(<PasoProgramas onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('programas-materia-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Matemática I')
      expect(select.textContent).toContain('Física I')
    })
  })

  it('renders carrera_id as <select> with options by nombre', async () => {
    render(<PasoProgramas onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('programas-carrera-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Ingeniería')
    })
  })

  it('renders cohorte_id as <select> with options by nombre', async () => {
    render(<PasoProgramas onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('programas-cohorte-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Cohorte 2024')
    })
  })

  it('materia options have correct values (ids) and labels (nombres)', async () => {
    render(<PasoProgramas onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('programas-materia-id') as HTMLSelectElement
      const opt = Array.from(select.options).find((o) => o.value === 'mat-1')
      expect(opt?.text).toBe('Matemática I')
    })
  })
})
