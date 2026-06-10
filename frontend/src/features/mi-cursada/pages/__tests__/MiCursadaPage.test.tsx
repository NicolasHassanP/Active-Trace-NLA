/**
 * MiCursadaPage render tests — task 6.5.
 * Tests: loading state, error state, datos con materias, estado vacío.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MiCursadaPage from '../MiCursadaPage'
import type { EstadoAcademicoRead } from '../../types'

vi.mock('../../services/miCursadaService', () => ({
  getEstadoAcademico: vi.fn(),
}))

import { getEstadoAcademico } from '../../services/miCursadaService'

const makeWrapper = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client: qc },
      createElement(MemoryRouter, null, children),
    )
}

const estadoVacio: EstadoAcademicoRead = {
  avance_global_pct: 0,
  total_actividades: 0,
  aprobadas: 0,
  materias: [],
  coloquios_reservados: [],
}

const estadoConDatos: EstadoAcademicoRead = {
  avance_global_pct: 50,
  total_actividades: 4,
  aprobadas: 2,
  materias: [
    {
      materia_id: 'mat-1',
      materia_nombre: 'Matemáticas',
      avance_pct: 50,
      total_actividades: 4,
      aprobadas: 2,
      calificaciones: [
        { actividad: 'TP1', nota_numerica: '8', nota_textual: null, aprobado: true, estado_entrega: 'aprobada' },
        { actividad: 'TP2', nota_numerica: null, nota_textual: null, aprobado: false, estado_entrega: 'sin_entrega' },
      ],
    },
  ],
  coloquios_reservados: [
    {
      evaluacion_id: 'eval-1',
      materia_nombre: 'Matemáticas',
      instancia: '1',
      tipo: 'Coloquio',
      fecha: '2026-07-15',
      franja: 'Mañana',
    },
  ],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('MiCursadaPage — loading', () => {
  it('shows loading message while fetching', () => {
    vi.mocked(getEstadoAcademico).mockImplementation(() => new Promise(() => {}))
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    expect(screen.getByText(/Cargando tu estado académico/)).toBeInTheDocument()
  })
})

describe('MiCursadaPage — error', () => {
  it('shows error state when fetch fails', async () => {
    vi.mocked(getEstadoAcademico).mockRejectedValue(new Error('Network error'))
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText('No se pudo cargar el estado académico')).toBeInTheDocument(),
    )
  })
})

describe('MiCursadaPage — estado vacío', () => {
  it('shows empty state for materias when none', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoVacio)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText('Sin materias registradas')).toBeInTheDocument(),
    )
  })

  it('shows empty coloquios panel when no reservations', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoVacio)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText('Sin coloquios reservados')).toBeInTheDocument(),
    )
  })
})

describe('MiCursadaPage — con datos', () => {
  it('renders materia nombre (at least once)', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoConDatos)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    // Matemáticas appears in materias section AND coloquios panel → use getAllBy
    await waitFor(() =>
      expect(screen.getAllByText('Matemáticas').length).toBeGreaterThan(0),
    )
  })

  it('renders avance_global_pct KPI label', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoConDatos)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    // '50%' appears in KpiCard value + ProgressBar span → use getAllBy
    await waitFor(() =>
      expect(screen.getAllByText('50%').length).toBeGreaterThan(0),
    )
  })

  it('renders avance global KPI section header', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoConDatos)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    await waitFor(() =>
      expect(screen.getByText('Avance global')).toBeInTheDocument(),
    )
  })

  it('renders coloquio tipo text', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoConDatos)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    // The coloquio panel shows "{tipo} · Instancia {instancia}"
    await waitFor(() =>
      expect(screen.getByText(/Instancia 1/)).toBeInTheDocument(),
    )
  })

  it('renders actividades with estado badge', async () => {
    vi.mocked(getEstadoAcademico).mockResolvedValue(estadoConDatos)
    render(<MiCursadaPage />, { wrapper: makeWrapper() })
    await waitFor(() => {
      expect(screen.getByText('TP1')).toBeInTheDocument()
      expect(screen.getByText('TP2')).toBeInTheDocument()
    })
  })
})
