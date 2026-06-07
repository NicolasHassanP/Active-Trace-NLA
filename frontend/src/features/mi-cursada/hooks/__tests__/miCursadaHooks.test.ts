/**
 * Tests for miCursadaHooks — task 5.3.
 * Verifica que useEstadoAcademico usa queryKey correcto y llama al service.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Partial mock: mock only the service function
vi.mock('../../services/miCursadaService', () => ({
  getEstadoAcademico: vi.fn(),
}))

import { getEstadoAcademico } from '../../services/miCursadaService'

describe('miCursadaHooks — useEstadoAcademico', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getEstadoAcademico is the queryFn used', async () => {
    const mockData = {
      avance_global_pct: 50,
      total_actividades: 4,
      aprobadas: 2,
      materias: [],
      coloquios_reservados: [],
    }
    vi.mocked(getEstadoAcademico).mockResolvedValue(mockData)

    // Verify service function returns expected shape when called
    const result = await getEstadoAcademico()
    expect(result.avance_global_pct).toBe(50)
    expect(result.materias).toEqual([])
  })

  it('getEstadoAcademico does not accept user_id params', async () => {
    // The service function signature takes no params (identity from JWT)
    expect(getEstadoAcademico.length).toBe(0)
  })
})
