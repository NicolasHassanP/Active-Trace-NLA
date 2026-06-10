/**
 * ComunicacionesPage and ComposeComunicacion tests.
 * Covers preview success/422, encolar success/422, bandeja render, polling terminal state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ComunicacionesPage from '../ComunicacionesPage'
import * as commService from '../../services/comunicacionService'
import * as authHook from '@/features/auth/hooks/useAuth'
import type { LoteStatusResponse } from '../../types'

vi.mock('../../services/comunicacionService')
vi.mock('@/features/auth/hooks/useAuth')
// C-27 — mock ComunicacionesHistorial to avoid rendering real component
vi.mock('../../components/ComunicacionesHistorial', () => ({
  default: () => <div data-testid="historial-panel">Historial Mock</div>,
}))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

const mockUseAuth = vi.mocked(authHook.useAuth)

const wrapper = (url = '/comunicaciones') => ({ children }: { children: React.ReactNode }) =>
  createElement(
    QueryClientProvider,
    { client: new QueryClient({ defaultOptions: { queries: { retry: false } } }) },
    createElement(
      MemoryRouter,
      { initialEntries: [url] },
      createElement(Routes, null,
        createElement(Route, { path: '/comunicaciones', element: children }),
      ),
    ),
  )

const mockLoteDone: LoteStatusResponse = {
  lote_id: 'lote1',
  mensajes: [
    {
      id: 'm1',
      tenant_id: 't1',
      lote_id: 'lote1',
      destinatario_email: 'a@t.com',
      asunto: 'Hola',
      cuerpo: 'Texto',
      estado: 'Enviado',
      enviado_por: null,
      aprobado_por: null,
      enviado_at: null,
      error_detalle: null,
      creado_en: '',
      actualizado_en: '',
    },
  ],
  pendientes: 0,
  enviados: 1,
  fallidos: 0,
  cancelados: 0,
}

beforeEach(() => {
  vi.clearAllMocks()
  mockUseAuth.mockReturnValue({
    user: null, tenantId: null, isAuthenticated: true, isInitializing: false, roles: ['COORDINADOR'],
    login: vi.fn(), logout: vi.fn(),
    isImpersonating: false, impersonatedName: null,
    impersonarUsuario: vi.fn(), finalizarImpersonacion: vi.fn(),
  })
})

describe('ComunicacionesPage', () => {
  it('renders the compose form', () => {
    render(<ComunicacionesPage />, { wrapper: wrapper() })
    expect(screen.getByTestId('compose-form')).toBeInTheDocument()
    expect(screen.getByTestId('asunto-input')).toBeInTheDocument()
    expect(screen.getByTestId('cuerpo-input')).toBeInTheDocument()
  })

  // C-27 — Tab tests
  it('shows tab Componer by default', () => {
    render(<ComunicacionesPage />, { wrapper: wrapper() })
    expect(screen.getByTestId('tab-componer')).toBeInTheDocument()
    expect(screen.getByTestId('tab-historial')).toBeInTheDocument()
    // Compose form visible
    expect(screen.getByTestId('compose-form')).toBeInTheDocument()
    // Historial NOT mounted
    expect(screen.queryByTestId('historial-panel')).not.toBeInTheDocument()
  })

  it('mounts ComunicacionesHistorial when clicking tab Historial', () => {
    render(<ComunicacionesPage />, { wrapper: wrapper() })
    fireEvent.click(screen.getByTestId('tab-historial'))
    expect(screen.getByTestId('historial-panel')).toBeInTheDocument()
    expect(screen.queryByTestId('compose-form')).not.toBeInTheDocument()
  })

  it('restores compose form when switching back to Componer', () => {
    render(<ComunicacionesPage />, { wrapper: wrapper() })
    // Go to historial
    fireEvent.click(screen.getByTestId('tab-historial'))
    expect(screen.getByTestId('historial-panel')).toBeInTheDocument()
    // Go back to componer
    fireEvent.click(screen.getByTestId('tab-componer'))
    expect(screen.getByTestId('compose-form')).toBeInTheDocument()
    expect(screen.queryByTestId('historial-panel')).not.toBeInTheDocument()
  })

  it('shows preloaded destinatarios count from URL params', () => {
    render(<ComunicacionesPage />, { wrapper: wrapper('/comunicaciones?destinatarios=a@t.com,b@t.com') })
    expect(screen.getByText(/2 destinatario/i)).toBeInTheDocument()
  })

  it('shows preview result on successful preview', async () => {
    vi.mocked(commService.previewComunicacion).mockResolvedValue({
      asunto: 'Hola Mundo', cuerpo: 'Texto renderizado',
    })
    render(<ComunicacionesPage />, { wrapper: wrapper('/comunicaciones?destinatarios=a@t.com') })
    fireEvent.change(screen.getByTestId('asunto-input'), { target: { value: 'Hola {{nombre}}' } })
    fireEvent.change(screen.getByTestId('cuerpo-input'), { target: { value: 'Texto' } })
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('preview-result')).toBeInTheDocument())
    expect(screen.getByText(/Hola Mundo/)).toBeInTheDocument()
  })

  it('shows 422 error and blocks encolar button on variable error', async () => {
    vi.mocked(commService.previewComunicacion).mockRejectedValue({
      status: 422, detail: 'variable {{nombre}} no resuelta',
    })
    render(<ComunicacionesPage />, { wrapper: wrapper('/comunicaciones?destinatarios=a@t.com') })
    fireEvent.change(screen.getByTestId('asunto-input'), { target: { value: 'Hola' } })
    fireEvent.change(screen.getByTestId('cuerpo-input'), { target: { value: 'Texto' } })
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('preview-error')).toBeInTheDocument())
    expect(screen.getByTestId('encolar-btn')).toBeDisabled()
  })

  it('shows lote bandeja after successful encolar', async () => {
    vi.mocked(commService.previewComunicacion).mockResolvedValue({ asunto: 'Hola', cuerpo: 'Texto' })
    vi.mocked(commService.encolarLote).mockResolvedValue({ lote_id: 'lote1', total_encolados: 1 })
    vi.mocked(commService.getLote).mockResolvedValue(mockLoteDone)
    render(<ComunicacionesPage />, { wrapper: wrapper('/comunicaciones?destinatarios=a@t.com') })
    fireEvent.change(screen.getByTestId('asunto-input'), { target: { value: 'Hola' } })
    fireEvent.change(screen.getByTestId('cuerpo-input'), { target: { value: 'Texto' } })
    // RN-16: preview must be confirmed before encolar is enabled
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('encolar-btn')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('encolar-btn'))
    await waitFor(() => expect(screen.getByTestId('lote-bandeja')).toBeInTheDocument())
  })

  it('shows aprobacion panel for COORDINADOR after lote is created', async () => {
    vi.mocked(commService.previewComunicacion).mockResolvedValue({ asunto: 'Hola', cuerpo: 'Texto' })
    vi.mocked(commService.encolarLote).mockResolvedValue({ lote_id: 'lote1', total_encolados: 1 })
    vi.mocked(commService.getLote).mockResolvedValue(mockLoteDone)
    render(<ComunicacionesPage />, { wrapper: wrapper('/comunicaciones?destinatarios=a@t.com') })
    fireEvent.change(screen.getByTestId('asunto-input'), { target: { value: 'Hola' } })
    fireEvent.change(screen.getByTestId('cuerpo-input'), { target: { value: 'Texto' } })
    // RN-16: preview must be confirmed before encolar is enabled
    fireEvent.click(screen.getByTestId('preview-btn'))
    await waitFor(() => expect(screen.getByTestId('encolar-btn')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('encolar-btn'))
    await waitFor(() => expect(screen.getByTestId('aprobacion-panel')).toBeInTheDocument())
  })
})
