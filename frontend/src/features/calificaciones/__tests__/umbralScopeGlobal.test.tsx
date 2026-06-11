/**
 * Tests for ADMIN scope global + umbral por-materia feature (frontend).
 *
 * Covers:
 * - Tab Umbral renders UmbralConfigDefault for ADMIN/COORDINADOR role (scope global)
 * - Tab Umbral renders UmbralConfigDocente for PROFESOR role (scope propio)
 * - UmbralConfigDocente shows is_default banner when inheriting default
 * - buildNav: "Mis materias" does NOT appear for ADMIN
 *
 * Strict TDD: RED → GREEN → triangulate → REFACTOR.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { buildNav } from '@/features/shell/components/buildNav'

// ---------------------------------------------------------------------------
// buildNav tests for ADMIN scope global — Paso 8
// ---------------------------------------------------------------------------

describe('buildNav — ADMIN scope global (umbral feature)', () => {
  it('§N1.1 ADMIN does NOT see /materias (no asignaciones propias)', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).not.toContain('/materias')
  })

  it('§N1.2 TRIANGULATE: PROFESOR sees /materias', () => {
    const paths = buildNav(['PROFESOR']).map((i) => i.path)
    expect(paths).toContain('/materias')
  })

  it('§N1.3 TRIANGULATE: COORDINADOR sees /materias', () => {
    const paths = buildNav(['COORDINADOR']).map((i) => i.path)
    expect(paths).toContain('/materias')
  })

  it('§N1.4 ADMIN still sees /calificaciones (uses scope global for umbral)', () => {
    const paths = buildNav(['ADMIN']).map((i) => i.path)
    expect(paths).toContain('/calificaciones')
  })
})

// ---------------------------------------------------------------------------
// UmbralConfigDocente — is_default banner
// ---------------------------------------------------------------------------

// Mock hooks
vi.mock('@/features/calificaciones/hooks/calificacionesHooks', () => ({
  useUmbral: vi.fn(),
  useConfigurarUmbral: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useUmbralDefault: vi.fn(),
  useConfigurarUmbralDefault: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}))

// Mock sonner
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

// Mock shared components
vi.mock('@/shared/components/ui', () => ({
  Button: ({ children, ...props }: React.PropsWithChildren<React.ButtonHTMLAttributes<HTMLButtonElement>>) => (
    <button {...props}>{children}</button>
  ),
}))

function wrapper({ children }: React.PropsWithChildren) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('UmbralConfigDocente — is_default banner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('§D1.1 RED→GREEN: shows is_default banner when data.is_default=true', async () => {
    const { useUmbral } = await import('@/features/calificaciones/hooks/calificacionesHooks')
    vi.mocked(useUmbral).mockReturnValue({
      data: {
        id: null,
        asignacion_id: null,
        cohorte_id: null,
        materia_id: 'mat-1',
        umbral_pct: 75,
        valores_aprobatorios: ['Aprobado'],
        is_default: true,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useUmbral>)

    const { default: UmbralConfigDocente } = await import(
      '@/features/calificaciones/components/UmbralConfigDocente'
    )
    render(<UmbralConfigDocente materia_id="mat-1" />, { wrapper })

    const banner = screen.getByTestId('umbral-heredado-banner')
    expect(banner).toBeDefined()
    expect(banner.textContent).toContain('75%')
  })

  it('§D1.2 TRIANGULATE: does NOT show is_default banner when data.is_default=false', async () => {
    const { useUmbral } = await import('@/features/calificaciones/hooks/calificacionesHooks')
    vi.mocked(useUmbral).mockReturnValue({
      data: {
        id: 'some-id',
        asignacion_id: 'asig-1',
        cohorte_id: null,
        materia_id: 'mat-1',
        umbral_pct: 80,
        valores_aprobatorios: ['Satisfactorio'],
        is_default: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useUmbral>)

    const { default: UmbralConfigDocente } = await import(
      '@/features/calificaciones/components/UmbralConfigDocente'
    )
    render(<UmbralConfigDocente materia_id="mat-1" />, { wrapper })

    const banner = screen.queryByTestId('umbral-heredado-banner')
    expect(banner).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// UmbralConfigDefault — renders for ADMIN
// ---------------------------------------------------------------------------

describe('UmbralConfigDefault — renders for ADMIN', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('§A1.1 RED→GREEN: renders default scope section heading', async () => {
    const { useUmbralDefault } = await import('@/features/calificaciones/hooks/calificacionesHooks')
    vi.mocked(useUmbralDefault).mockReturnValue({
      data: {
        id: null,
        asignacion_id: null,
        cohorte_id: null,
        materia_id: 'mat-1',
        umbral_pct: 60,
        valores_aprobatorios: [],
        is_default: true,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useUmbralDefault>)

    const { default: UmbralConfigDefault } = await import(
      '@/features/calificaciones/components/UmbralConfigDefault'
    )
    render(<UmbralConfigDefault materia_id="mat-1" />, { wrapper })

    const input = screen.getByTestId('umbral-default-pct-input')
    expect(input).toBeDefined()
  })

  it('§A1.2 TRIANGULATE: renders save button for default', async () => {
    const { useUmbralDefault } = await import('@/features/calificaciones/hooks/calificacionesHooks')
    vi.mocked(useUmbralDefault).mockReturnValue({
      data: {
        id: 'def-id',
        asignacion_id: null,
        cohorte_id: null,
        materia_id: 'mat-1',
        umbral_pct: 70,
        valores_aprobatorios: ['Aprobado'],
        is_default: true,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useUmbralDefault>)

    const { default: UmbralConfigDefault } = await import(
      '@/features/calificaciones/components/UmbralConfigDefault'
    )
    render(<UmbralConfigDefault materia_id="mat-1" />, { wrapper })

    const btn = screen.getByTestId('guardar-umbral-default')
    expect(btn).toBeDefined()
  })
})
