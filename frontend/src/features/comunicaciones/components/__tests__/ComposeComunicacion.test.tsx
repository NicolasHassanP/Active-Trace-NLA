/**
 * ComposeComunicacion — RN-16 gate tests.
 *
 * Covers:
 *   (a) "Encolar" deshabilitado al montar sin preview
 *   (b) "Encolar" habilitado tras preview exitoso
 *   (c) "Encolar" vuelve a deshabilitarse al editar la plantilla después de previsualizar
 *   (d) "Encolar" sigue deshabilitado si no hay destinatarios (aunque hubiese preview)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ComposeComunicacion from '../ComposeComunicacion'
import * as hooks from '../../hooks/comunicacionHooks'
import type { AlumnoAtrasado } from '@/features/atrasados/types'

vi.mock('../../hooks/comunicacionHooks')

// ---- Helpers ----

const makeDestinatario = (id = '1'): AlumnoAtrasado => ({
  entrada_padron_id: id,
  nombre: 'Ana',
  apellidos: 'García',
  email: `ana${id}@test.com`,
  actividades_faltantes: ['TP1'],
  actividades_no_aprobadas: [],
})

const wrapper = () =>
  ({ children }: { children: React.ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client: new QueryClient({ defaultOptions: { queries: { retry: false } } }) },
      children,
    )

/** Creates a preview mutation mock that will call onSuccess with a preview result */
function mockPreviewSuccess() {
  vi.mocked(hooks.usePreviewComunicacion).mockReturnValue({
    mutate: vi.fn((_req, opts) => {
      opts?.onSuccess?.({ asunto: 'Asunto renderizado', cuerpo: 'Cuerpo renderizado' }, _req, undefined)
    }),
    isPending: false,
  } as any)
}

/** Creates a preview mutation mock that is idle (never called yet) */
function mockPreviewIdle() {
  vi.mocked(hooks.usePreviewComunicacion).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as any)
}

function mockEncolarIdle() {
  vi.mocked(hooks.useEncolarLote).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as any)
}

// ---- Tests ----

beforeEach(() => {
  vi.clearAllMocks()
  mockEncolarIdle()
})

describe('ComposeComunicacion — RN-16 preview gate', () => {
  // (a) Encolar disabled on mount without preview
  it('disables "Encolar" on mount before any preview', () => {
    mockPreviewIdle()
    render(<ComposeComunicacion destinatarios={[makeDestinatario()]} />, { wrapper: wrapper() })

    expect(screen.getByTestId('encolar-btn')).toBeDisabled()
  })

  // Hint visible when no preview and has recipients
  it('shows hint text when no preview has been confirmed', () => {
    mockPreviewIdle()
    render(<ComposeComunicacion destinatarios={[makeDestinatario()]} />, { wrapper: wrapper() })

    expect(screen.getByTestId('preview-hint')).toBeInTheDocument()
    expect(screen.getByText(/previsualizá antes de encolar/i)).toBeInTheDocument()
  })

  // (b) Encolar enabled after successful preview
  it('enables "Encolar" after a successful preview', async () => {
    mockPreviewSuccess()
    render(<ComposeComunicacion destinatarios={[makeDestinatario()]} />, { wrapper: wrapper() })

    // Initially disabled
    expect(screen.getByTestId('encolar-btn')).toBeDisabled()

    // Trigger preview
    fireEvent.click(screen.getByTestId('preview-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('encolar-btn')).not.toBeDisabled()
    })
  })

  // Hint disappears once preview confirmed
  it('hides the preview hint once preview is confirmed', async () => {
    mockPreviewSuccess()
    render(<ComposeComunicacion destinatarios={[makeDestinatario()]} />, { wrapper: wrapper() })

    fireEvent.click(screen.getByTestId('preview-btn'))

    await waitFor(() => {
      expect(screen.queryByTestId('preview-hint')).not.toBeInTheDocument()
    })
  })

  // (c) Encolar disabled again after editing template post-preview
  it('disables "Encolar" again when asunto is edited after a successful preview', async () => {
    mockPreviewSuccess()
    render(<ComposeComunicacion destinatarios={[makeDestinatario()]} />, { wrapper: wrapper() })

    // Confirm preview
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('encolar-btn')).not.toBeDisabled())

    // Edit the asunto — should reset the gate
    const asuntoInput = screen.getByTestId('asunto-input')
    fireEvent.change(asuntoInput, { target: { value: 'Nuevo asunto cambiado' } })

    await waitFor(() => {
      expect(screen.getByTestId('encolar-btn')).toBeDisabled()
    })
  })

  // Triangulation: editing cuerpo also resets the gate
  it('disables "Encolar" again when cuerpo is edited after a successful preview', async () => {
    mockPreviewSuccess()
    render(<ComposeComunicacion destinatarios={[makeDestinatario()]} />, { wrapper: wrapper() })

    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('encolar-btn')).not.toBeDisabled())

    // Edit the cuerpo
    const cuerpoInput = screen.getByTestId('cuerpo-input')
    fireEvent.change(cuerpoInput, { target: { value: 'Nuevo cuerpo cambiado' } })

    await waitFor(() => {
      expect(screen.getByTestId('encolar-btn')).toBeDisabled()
    })
  })

  // (d) Encolar disabled when no destinatarios, even if preview would succeed
  it('disables "Encolar" when there are no destinatarios', () => {
    mockPreviewIdle()
    render(<ComposeComunicacion destinatarios={[]} />, { wrapper: wrapper() })

    expect(screen.getByTestId('encolar-btn')).toBeDisabled()
  })

  // Hint hidden when no recipients (no sense showing it without recipients)
  it('hides the preview hint when destinatarios is empty', () => {
    mockPreviewIdle()
    render(<ComposeComunicacion destinatarios={[]} />, { wrapper: wrapper() })

    expect(screen.queryByTestId('preview-hint')).not.toBeInTheDocument()
  })
})
