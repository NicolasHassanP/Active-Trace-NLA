/**
 * Tests for AuditoriaMetricasPanel.
 * Covers: renders KPI sections, actor_nombre/materia_nombre fallbacks.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import AuditoriaMetricasPanel from '../AuditoriaMetricasPanel'
import * as hooks from '../../hooks/auditoriaHooks'
import type {
  AccionesPorDiaResponse,
  InteraccionesDocenteResponse,
  InteraccionesDocenteMateriaResponse,
  ComunicacionesPorDocenteResponse,
  AuditEventRead,
} from '../../types'

vi.mock('../../hooks/auditoriaHooks')

const sampleAcciones: AccionesPorDiaResponse = { items: [{ dia: '2026-06-01T00:00:00', total: 5 }] }

const sampleInteracciones: InteraccionesDocenteResponse = {
  items: [{ actor_user_id: 'auth-id-1', accion: 'LOGIN', total: 3, actor_nombre: 'Ana García' }],
}

const sampleInteraccionesMat: InteraccionesDocenteMateriaResponse = {
  items: [{
    actor_user_id: 'auth-id-1',
    materia_id: 'mat-1',
    total: 2,
    actor_nombre: 'Ana García',
    materia_nombre: 'Legislación 1',
  }],
}

const sampleComunicaciones: ComunicacionesPorDocenteResponse = {
  items: [{ enviado_por: 'usr-1', estado: 'ENVIADA', total: 10 }],
}

const sampleUltimas: AuditEventRead[] = [{
  id: 'evt-1',
  tenant_id: 'ten-1',
  actor_user_id: 'auth-id-1',
  impersonated_user_id: null,
  accion: 'LOGIN',
  modulo: 'auth',
  entidad_tipo: 'Usuario',
  entidad_id: null,
  resultado: 'ok',
  registros_afectados: null,
  ip: null,
  user_agent: null,
  before: null,
  after: null,
  created_at: '2026-06-01T10:00:00',
  actor_nombre: 'Ana García',
  entidad_nombre: null,
}]

// Orphan actor (no matching domain user)
const sampleInteraccionesOrfano: InteraccionesDocenteResponse = {
  items: [{ actor_user_id: 'orphan-id', accion: 'LOGIN', total: 1, actor_nombre: null }],
}

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return wrapper
}

describe('AuditoriaMetricasPanel', () => {
  beforeEach(() => {
    vi.mocked(hooks.useAccionesPorDia).mockReturnValue({ data: sampleAcciones, isLoading: false, isError: false } as ReturnType<typeof hooks.useAccionesPorDia>)
    vi.mocked(hooks.useInteraccionesDocente).mockReturnValue({ data: sampleInteracciones, isLoading: false, isError: false } as ReturnType<typeof hooks.useInteraccionesDocente>)
    vi.mocked(hooks.useInteraccionesDocenteMateria).mockReturnValue({ data: sampleInteraccionesMat, isLoading: false, isError: false } as ReturnType<typeof hooks.useInteraccionesDocenteMateria>)
    vi.mocked(hooks.useComunicacionesPorDocente).mockReturnValue({ data: sampleComunicaciones, isLoading: false, isError: false } as ReturnType<typeof hooks.useComunicacionesPorDocente>)
    vi.mocked(hooks.useUltimasAcciones).mockReturnValue({ data: sampleUltimas, isLoading: false, isError: false } as ReturnType<typeof hooks.useUltimasAcciones>)
  })

  afterEach(() => vi.restoreAllMocks())

  it('renders the acciones-por-dia section heading', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('metricas-acciones-por-dia')).toBeInTheDocument()
  })

  it('renders the interacciones-docente section', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('metricas-interacciones-docente')).toBeInTheDocument()
  })

  it('renders actor_nombre in interacciones-docente (not raw UUID)', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    const section = screen.getByTestId('metricas-interacciones-docente')
    expect(section).toHaveTextContent('Ana García')
    expect(section).not.toHaveTextContent('auth-id-1')
  })

  it('renders the interacciones-docente-materia section', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('metricas-interacciones-docente-materia')).toBeInTheDocument()
  })

  it('renders actor_nombre and materia_nombre in interacciones-docente-materia', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    const section = screen.getByTestId('metricas-interacciones-docente-materia')
    expect(section).toHaveTextContent('Ana García')
    expect(section).toHaveTextContent('Legislación 1')
    expect(section).not.toHaveTextContent('auth-id-1')
    expect(section).not.toHaveTextContent('mat-1')
  })

  it('renders the comunicaciones-por-docente section', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('metricas-comunicaciones-por-docente')).toBeInTheDocument()
  })

  it('renders the ultimas-acciones section', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('metricas-ultimas-acciones')).toBeInTheDocument()
  })

  it('renders actor_nombre in ultimas-acciones (not raw UUID)', () => {
    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    const section = screen.getByTestId('metricas-ultimas-acciones')
    expect(section).toHaveTextContent('Ana García')
    expect(section).not.toHaveTextContent('auth-id-1')
  })

  it('shows "(desconocido)" fallback in interacciones-docente for orphan actor', () => {
    vi.mocked(hooks.useInteraccionesDocente).mockReturnValue({
      data: sampleInteraccionesOrfano,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof hooks.useInteraccionesDocente>)

    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    const section = screen.getByTestId('metricas-interacciones-docente')
    expect(section).toHaveTextContent('(desconocido)')
  })

  it('shows "(desconocido)" fallback in ultimas-acciones for null actor_nombre', () => {
    const ultrasSinNombre: AuditEventRead[] = [{ ...sampleUltimas[0], actor_nombre: null }]
    vi.mocked(hooks.useUltimasAcciones).mockReturnValue({
      data: ultrasSinNombre,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof hooks.useUltimasAcciones>)

    render(<AuditoriaMetricasPanel />, { wrapper: makeWrapper() })
    const section = screen.getByTestId('metricas-ultimas-acciones')
    expect(section).toHaveTextContent('(desconocido)')
  })
})
