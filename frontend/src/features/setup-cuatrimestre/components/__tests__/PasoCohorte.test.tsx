/**
 * PasoCohorte render tests.
 *
 * Verifies the cohorte field is a <select> by nombre (no raw UUID/id input),
 * and selecting a cohorte derives the período and confirms with its id.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import PasoCohorte from '../PasoCohorte'
import type { CohorteItem } from '@/features/monitores/types'

vi.mock('@/features/monitores/services/monitoresService', () => ({
  listarTodosCohortes: vi.fn(),
}))

import { listarTodosCohortes } from '@/features/monitores/services/monitoresService'

const mockCohortes = vi.mocked(listarTodosCohortes)

const sampleCohortes: CohorteItem[] = [
  { id: 'coh-1', carrera_id: 'car-1', nombre: 'Cohorte 2026-1', anio: 2026, estado: 'activo' },
  { id: 'coh-2', carrera_id: 'car-1', nombre: 'Cohorte 2026-2', anio: 2026, estado: 'activo' },
]

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
}

beforeEach(() => {
  mockCohortes.mockResolvedValue(sampleCohortes)
})

describe('PasoCohorte — render', () => {
  it('renders the cohorte field as a select with options by nombre', async () => {
    render(<PasoCohorte onSuccess={vi.fn()} onError={vi.fn()} />, { wrapper: makeWrapper() })

    await waitFor(() => {
      const select = screen.getByTestId('cohorte-id')
      expect(select.tagName.toLowerCase()).toBe('select')
      expect(select.textContent).toContain('Cohorte 2026-1')
      expect(select.textContent).toContain('Cohorte 2026-2')
    })
  })

  it('confirms with the selected cohorte_id and derives the período', async () => {
    const onSuccess = vi.fn()
    render(<PasoCohorte onSuccess={onSuccess} onError={vi.fn()} />, { wrapper: makeWrapper() })

    // Wait for the async options to load before selecting one.
    const select = await screen.findByTestId('cohorte-id')
    await waitFor(() => expect(select.textContent).toContain('Cohorte 2026-2'))

    fireEvent.change(select, { target: { value: 'coh-2' } })

    // Derived período is shown (read-only).
    await waitFor(() => expect(screen.getByText(/Período:/)).toBeTruthy())

    fireEvent.click(screen.getByText('Confirmar cohorte'))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith('coh-2'))
  })
})
