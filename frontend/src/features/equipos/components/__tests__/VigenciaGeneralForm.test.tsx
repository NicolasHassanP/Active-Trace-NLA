/**
 * VigenciaGeneralForm render tests.
 *
 * Verifies materia/carrera/cohorte render as <select> by nombre (no raw UUID inputs).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import VigenciaGeneralForm from '../VigenciaGeneralForm'
import type { MateriaItem, CohorteItem, CarreraItem } from '@/features/monitores/types'

vi.mock('@/features/monitores/services/monitoresService', () => ({
  listarTodasMaterias: vi.fn(),
  listarTodosCohortes: vi.fn(),
  listarTodasCarreras: vi.fn(),
}))

vi.mock('../../hooks/equiposHooks', () => ({
  useVigenciaGeneral: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
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

describe('VigenciaGeneralForm — render', () => {
  it('renders materia/carrera/cohorte as selects with options by nombre', async () => {
    render(<VigenciaGeneralForm />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const materia = screen.getByTestId('vigencia-materia-id')
      expect(materia.tagName.toLowerCase()).toBe('select')
      expect(materia.textContent).toContain('Matemática I')
    })

    expect(screen.getByTestId('vigencia-carrera-id').textContent).toContain('Ingeniería')
    expect(screen.getByTestId('vigencia-cohorte-id').textContent).toContain('Cohorte 2024')
  })
})
