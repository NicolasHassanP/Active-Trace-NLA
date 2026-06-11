/**
 * PasoClonarEquipo render tests.
 *
 * Verifies:
 *   - All 6 selects (origen/destino × materia/carrera/cohorte) render with options by nombre
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import PasoClonarEquipo from '../PasoClonarEquipo'
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
  { id: 'coh-2', carrera_id: 'car-1', nombre: 'Cohorte 2025', anio: 2025, estado: 'activo' },
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

describe('PasoClonarEquipo — render', () => {
  it('renders the form with data-testid paso-clonar-equipo', () => {
    render(<PasoClonarEquipo onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('paso-clonar-equipo')).toBeTruthy()
  })

  it('renders origen-materia-id as <select> with options by nombre', async () => {
    render(<PasoClonarEquipo onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('clonar-origen-materia-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Matemática I')
      expect(select.textContent).toContain('Física I')
    })
  })

  it('renders destino-materia-id as <select> with options by nombre', async () => {
    render(<PasoClonarEquipo onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('clonar-destino-materia-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Matemática I')
    })
  })

  it('renders origen-carrera-id and destino-carrera-id as <select>', async () => {
    render(<PasoClonarEquipo onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('clonar-origen-carrera-id').tagName.toLowerCase()).toBe('select')
      expect(screen.getByTestId('clonar-destino-carrera-id').tagName.toLowerCase()).toBe('select')
      expect(screen.getByTestId('clonar-origen-carrera-id').textContent).toContain('Ingeniería')
    })
  })

  it('renders origen-cohorte-id and destino-cohorte-id as <select>', async () => {
    render(<PasoClonarEquipo onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('clonar-origen-cohorte-id').tagName.toLowerCase()).toBe('select')
      expect(screen.getByTestId('clonar-destino-cohorte-id').tagName.toLowerCase()).toBe('select')
      expect(screen.getByTestId('clonar-origen-cohorte-id').textContent).toContain('Cohorte 2024')
      expect(screen.getByTestId('clonar-origen-cohorte-id').textContent).toContain('Cohorte 2025')
    })
  })

  it('cohorte options have correct values (ids) and labels (nombres)', async () => {
    render(<PasoClonarEquipo onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('clonar-origen-cohorte-id') as HTMLSelectElement
      const opt = Array.from(select.options).find((o) => o.value === 'coh-1')
      expect(opt?.text).toBe('Cohorte 2024')
    })
  })
})
