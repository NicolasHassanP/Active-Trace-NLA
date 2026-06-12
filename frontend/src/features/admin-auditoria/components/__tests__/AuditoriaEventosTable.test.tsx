/**
 * Tests for AuditoriaEventosTable.
 * Covers: renders rows, pagination (next disabled when < limit), filters.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AuditoriaEventosTable from '../AuditoriaEventosTable'
import type { AuditEventRead, AuditoriaFiltros } from '../../types'

const makeEvent = (id: string, accion = 'LOGIN'): AuditEventRead => ({
  id,
  tenant_id: 'ten-1',
  actor_user_id: 'usr-1',
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
    // Should show first event's accion
    expect(screen.getAllByText('LOGIN').length).toBeGreaterThan(0)
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
})
