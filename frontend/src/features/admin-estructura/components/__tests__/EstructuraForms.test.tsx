/**
 * Tests for EstructuraForms — CarreraForm, MateriaForm, CohorteForm.
 * RHF + Zod validation, submit callbacks, 409/404 error display via parseDomainError.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import CarreraForm from '../CarreraForm'
import MateriaForm from '../MateriaForm'
import CohorteForm from '../CohorteForm'
import type { CarreraRead, MateriaRead, CohorteRead } from '../../types'

const sampleCarrera: CarreraRead = {
  id: 'car-1', codigo: 'ING', nombre: 'Ingeniería', estado: 'activa',
  created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00',
}
const sampleMateria: MateriaRead = {
  id: 'mat-1', codigo: 'MAT1', nombre: 'Matemática I', estado: 'activa',
  created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00',
}
const sampleCohorte: CohorteRead = {
  id: 'coh-1', carrera_id: 'car-1', nombre: '2026', anio: 2026,
  vig_desde: '2026-03-01', vig_hasta: null, estado: 'activa',
  created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00',
}

const sampleCarreras: CarreraRead[] = [sampleCarrera]

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  return wrapper
}

// ── CarreraForm ───────────────────────────────────────────────────────────────

describe('CarreraForm', () => {
  it('renders in create mode with empty fields', () => {
    render(<CarreraForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />, { wrapper: makeWrapper() })
    const codigoInput = screen.getByTestId('carrera-codigo') as HTMLInputElement
    expect(codigoInput.value).toBe('')
  })

  it('renders in edit mode with pre-filled fields', () => {
    render(
      <CarreraForm initialValues={sampleCarrera} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )
    const codigoInput = screen.getByTestId('carrera-codigo') as HTMLInputElement
    expect(codigoInput.value).toBe('ING')
  })

  it('calls onSubmit with correct values on valid submit', async () => {
    const onSubmit = vi.fn()
    render(<CarreraForm onSubmit={onSubmit} onCancel={vi.fn()} isSubmitting={false} />, { wrapper: makeWrapper() })

    fireEvent.change(screen.getByTestId('carrera-codigo'), { target: { value: 'NEW' } })
    fireEvent.change(screen.getByTestId('carrera-nombre'), { target: { value: 'Nueva Carrera' } })
    fireEvent.click(screen.getByTestId('carrera-submit'))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce())
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ codigo: 'NEW', nombre: 'Nueva Carrera' }))
  })

  it('shows validation error when codigo is empty', async () => {
    render(<CarreraForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />, { wrapper: makeWrapper() })
    fireEvent.click(screen.getByTestId('carrera-submit'))
    await waitFor(() => expect(screen.getByTestId('carrera-codigo-error')).toBeInTheDocument())
  })

  it('displays domain error message when errorMessage prop is provided', () => {
    render(
      <CarreraForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} errorMessage="Código duplicado" />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByText('Código duplicado')).toBeInTheDocument()
  })

  it('never includes tenant_id in submitted values', async () => {
    const onSubmit = vi.fn()
    render(<CarreraForm onSubmit={onSubmit} onCancel={vi.fn()} isSubmitting={false} />, { wrapper: makeWrapper() })

    fireEvent.change(screen.getByTestId('carrera-codigo'), { target: { value: 'C1' } })
    fireEvent.change(screen.getByTestId('carrera-nombre'), { target: { value: 'Test' } })
    fireEvent.click(screen.getByTestId('carrera-submit'))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce())
    const submitted = onSubmit.mock.calls[0][0] as Record<string, unknown>
    expect(submitted).not.toHaveProperty('tenant_id')
  })
})

// ── MateriaForm ───────────────────────────────────────────────────────────────

describe('MateriaForm', () => {
  it('renders in create mode', () => {
    render(<MateriaForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />, { wrapper: makeWrapper() })
    expect(screen.getByTestId('materia-codigo')).toBeInTheDocument()
  })

  it('pre-fills in edit mode', () => {
    render(
      <MateriaForm initialValues={sampleMateria} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )
    const codigoInput = screen.getByTestId('materia-codigo') as HTMLInputElement
    expect(codigoInput.value).toBe('MAT1')
  })

  it('calls onSubmit with valid values', async () => {
    const onSubmit = vi.fn()
    render(<MateriaForm onSubmit={onSubmit} onCancel={vi.fn()} isSubmitting={false} />, { wrapper: makeWrapper() })

    fireEvent.change(screen.getByTestId('materia-codigo'), { target: { value: 'FIS1' } })
    fireEvent.change(screen.getByTestId('materia-nombre'), { target: { value: 'Física I' } })
    fireEvent.click(screen.getByTestId('materia-submit'))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce())
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ codigo: 'FIS1', nombre: 'Física I' }))
  })

  it('displays error message when errorMessage provided', () => {
    render(
      <MateriaForm onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} errorMessage="Código duplicado" />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByText('Código duplicado')).toBeInTheDocument()
  })
})

// ── CohorteForm ───────────────────────────────────────────────────────────────

describe('CohorteForm', () => {
  it('renders with carrera selector', () => {
    render(
      <CohorteForm carreras={sampleCarreras} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByTestId('cohorte-carrera-id')).toBeInTheDocument()
  })

  it('pre-fills in edit mode', () => {
    render(
      <CohorteForm
        carreras={sampleCarreras}
        initialValues={sampleCohorte}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
      />,
      { wrapper: makeWrapper() },
    )
    const nombreInput = screen.getByTestId('cohorte-nombre') as HTMLInputElement
    expect(nombreInput.value).toBe('2026')
  })

  it('submits with vig_hasta null when left empty (cohorte abierta)', async () => {
    const onSubmit = vi.fn()
    render(
      <CohorteForm carreras={sampleCarreras} onSubmit={onSubmit} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )

    // Select carrera
    fireEvent.change(screen.getByTestId('cohorte-carrera-id'), { target: { value: 'car-1' } })
    fireEvent.change(screen.getByTestId('cohorte-nombre'), { target: { value: '2026' } })
    fireEvent.change(screen.getByTestId('cohorte-anio'), { target: { value: '2026' } })
    fireEvent.change(screen.getByTestId('cohorte-vig-desde'), { target: { value: '2026-03-01' } })
    // vig_hasta left empty

    fireEvent.click(screen.getByTestId('cohorte-submit'))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce())
    const submitted = onSubmit.mock.calls[0][0] as Record<string, unknown>
    expect(submitted.vig_hasta === null || submitted.vig_hasta === '' || submitted.vig_hasta === undefined).toBe(true)
  })

  it('requires carrera_id and shows error when missing', async () => {
    render(
      <CohorteForm carreras={sampleCarreras} onSubmit={vi.fn()} onCancel={vi.fn()} isSubmitting={false} />,
      { wrapper: makeWrapper() },
    )
    // Leave carrera unselected
    fireEvent.change(screen.getByTestId('cohorte-nombre'), { target: { value: 'X' } })
    fireEvent.change(screen.getByTestId('cohorte-anio'), { target: { value: '2026' } })
    fireEvent.change(screen.getByTestId('cohorte-vig-desde'), { target: { value: '2026-03-01' } })
    fireEvent.click(screen.getByTestId('cohorte-submit'))

    await waitFor(() => expect(screen.getByTestId('cohorte-carrera-error')).toBeInTheDocument())
  })

  it('displays domain error message when errorMessage provided', () => {
    render(
      <CohorteForm
        carreras={sampleCarreras}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        isSubmitting={false}
        errorMessage="Carrera inactiva"
      />,
      { wrapper: makeWrapper() },
    )
    expect(screen.getByText('Carrera inactiva')).toBeInTheDocument()
  })
})
