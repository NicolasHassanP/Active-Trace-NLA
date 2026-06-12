/**
 * Tests for AuditoriaEventosTable.
 * Covers: renders rows with actor_nombre/entidad_nombre, pagination,
 * client-side actor name filter, entidad label mapping.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AuditoriaEventosTable from '../AuditoriaEventosTable'
import type { AuditEventRead, AuditoriaFiltros } from '../../types'

const makeEvent = (
  id: string,
  accion = 'LOGIN',
  overrides: Partial<AuditEventRead> = {},
): AuditEventRead => ({
  id,
  tenant_id: 'ten-1',
  actor_user_id: 'auth-id-1',
  impersonated_user_id: null,
  accion,
  modulo: 'auth',
  entidad_tipo: 'Usuario',
  entidad_id: null,
  resultado: 'ok',
  registros_afectados: null,
  ip: '127.0.0.1',
  user_agent: null,
  before: null,
  after: null,
  created_at: '2026-06-01T10:00:00',
  actor_nombre: 'Ana García',
  entidad_nombre: null,
  ...overrides,
})

const events10 = Array.from({ length: 10 }, (_, i) => makeEvent(`evt-${i}`, i % 2 === 0 ? 'LOGIN' : 'LOGOUT'))
const events5 = Array.from({ length: 5 }, (_, i) => makeEvent(`evt-${i}`))

const defaultFiltros: AuditoriaFiltros = { limit: 10, offset: 0 }

describe('AuditoriaEventosTable', () => {
  it('renders event rows', () => {
    render(
      <AuditoriaEventosTable
        events={events10}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getAllByText('LOGIN').length).toBeGreaterThan(0)
  })

  it('shows actor_nombre instead of UUID', () => {
    render(
      <AuditoriaEventosTable
        events={[makeEvent('e1')]}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByText('Ana García')).toBeInTheDocument()
    // Should NOT show the raw UUID
    expect(screen.queryByText(/auth-id-1/)).not.toBeInTheDocument()
  })

  it('shows "(desconocido)" when actor_nombre is null', () => {
    render(
      <AuditoriaEventosTable
        events={[makeEvent('e1', 'LOGIN', { actor_nombre: null })]}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByText('(desconocido)')).toBeInTheDocument()
  })

  it('shows entidad_nombre with label when available (e.g. Materia)', () => {
    render(
      <AuditoriaEventosTable
        events={[makeEvent('e1', 'ESTRUCTURA_GESTIONAR', {
          entidad_tipo: 'Materia',
          entidad_id: 'some-uuid',
          entidad_nombre: 'Legislación 1',
        })]}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByText('Materia: Legislación 1')).toBeInTheDocument()
  })

  it('shows readable label when entidad_nombre is null (FechaAcademica)', () => {
    render(
      <AuditoriaEventosTable
        events={[makeEvent('e1', 'FECHA_ACADEMICA_GESTIONAR', {
          entidad_tipo: 'FechaAcademica',
          entidad_id: 'some-uuid',
          entidad_nombre: null,
        })]}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByText('Fecha académica')).toBeInTheDocument()
    // Must NOT show raw UUID
    expect(screen.queryByText(/some-uuid/)).not.toBeInTheDocument()
  })

  it('shows empty state when no events', () => {
    render(
      <AuditoriaEventosTable
        events={[]}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByTestId('auditoria-eventos-empty')).toBeInTheDocument()
  })

  it('disables siguiente button when events < limit (last page)', () => {
    render(
      <AuditoriaEventosTable
        events={events5}
        filtros={{ limit: 10, offset: 0 }}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    const siguiente = screen.getByTestId('btn-siguiente') as HTMLButtonElement
    expect(siguiente.disabled).toBe(true)
  })

  it('enables siguiente button when events == limit (may have more)', () => {
    render(
      <AuditoriaEventosTable
        events={events10}
        filtros={{ limit: 10, offset: 0 }}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    const siguiente = screen.getByTestId('btn-siguiente') as HTMLButtonElement
    expect(siguiente.disabled).toBe(false)
  })

  it('disables anterior button on first page (offset 0)', () => {
    render(
      <AuditoriaEventosTable
        events={events10}
        filtros={{ limit: 10, offset: 0 }}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    const anterior = screen.getByTestId('btn-anterior') as HTMLButtonElement
    expect(anterior.disabled).toBe(true)
  })

  it('calls onFiltrosChange with incremented offset on siguiente click', () => {
    const onChange = vi.fn()
    render(
      <AuditoriaEventosTable
        events={events10}
        filtros={{ limit: 10, offset: 0 }}
        onFiltrosChange={onChange}
        isLoading={false}
      />,
    )
    fireEvent.click(screen.getByTestId('btn-siguiente'))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ offset: 10 }))
  })

  it('calls onFiltrosChange with decremented offset on anterior click', () => {
    const onChange = vi.fn()
    render(
      <AuditoriaEventosTable
        events={events10}
        filtros={{ limit: 10, offset: 10 }}
        onFiltrosChange={onChange}
        isLoading={false}
      />,
    )
    fireEvent.click(screen.getByTestId('btn-anterior'))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ offset: 0 }))
  })

  it('renders actor search input with label "Actor"', () => {
    render(
      <AuditoriaEventosTable
        events={events10}
        filtros={defaultFiltros}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    const input = screen.getByRole('textbox', { name: /Actor/i })
    expect(input).toBeInTheDocument()
  })

  it('filters events client-side by actor_nombre substring (case-insensitive)', () => {
    const mixed = [
      makeEvent('e1', 'LOGIN', { actor_nombre: 'Ana García' }),
      makeEvent('e2', 'LOGIN', { actor_nombre: 'Pedro López' }),
    ]
    render(
      <AuditoriaEventosTable
        events={mixed}
        filtros={{ ...defaultFiltros, actor_nombre_q: 'ana' }}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByText('Ana García')).toBeInTheDocument()
    expect(screen.queryByText('Pedro López')).not.toBeInTheDocument()
  })

  it('shows all events when actor_nombre_q is empty', () => {
    const mixed = [
      makeEvent('e1', 'LOGIN', { actor_nombre: 'Ana García' }),
      makeEvent('e2', 'LOGIN', { actor_nombre: 'Pedro López' }),
    ]
    render(
      <AuditoriaEventosTable
        events={mixed}
        filtros={{ ...defaultFiltros, actor_nombre_q: '' }}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByText('Ana García')).toBeInTheDocument()
    expect(screen.getByText('Pedro López')).toBeInTheDocument()
  })

  it('shows empty state when actor filter matches nothing', () => {
    render(
      <AuditoriaEventosTable
        events={[makeEvent('e1', 'LOGIN', { actor_nombre: 'Ana García' })]}
        filtros={{ ...defaultFiltros, actor_nombre_q: 'NOMATCH' }}
        onFiltrosChange={vi.fn()}
        isLoading={false}
      />,
    )
    expect(screen.getByTestId('auditoria-eventos-empty')).toBeInTheDocument()
  })
})
