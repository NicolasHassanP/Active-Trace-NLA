/**
 * InboxPage render tests — task 7.4.
 * Tests: render de lista, estado vacío, apertura de hilo,
 * distinción de mensaje propio, submit de nuevo hilo y respuesta, errores 404/409.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import InboxPage from '../InboxPage'
import type { InboxHiloRead, MensajeRead } from '../../types'

// Partial mock: preserve real Zod schemas, mock only service functions
vi.mock('../../services/mensajeriaService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../services/mensajeriaService')>()
  return {
    ...actual,
    listarHilos: vi.fn(),
    abrirHilo: vi.fn(),
    iniciarHilo: vi.fn(),
    responder: vi.fn(),
  }
})

vi.mock('@/features/auth/hooks/useAuth', () => ({ useAuth: vi.fn() }))

import { useAuth } from '@/features/auth/hooks/useAuth'
import * as service from '../../services/mensajeriaService'

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, createElement(MemoryRouter, null, children))
}

const CURRENT_USER_ID = 'user-current-uuid'

const sampleHilo: InboxHiloRead = {
  id: 'hilo-1',
  asunto: 'Consulta de notas',
  no_leidos: 2,
  ultimo_mensaje_at: '2024-03-10T15:00:00',
  otro_participante_nombre: null,
}

const mensajePropio: MensajeRead = {
  id: 'msg-1',
  hilo_id: 'hilo-1',
  remitente_id: CURRENT_USER_ID,
  asunto: 'Re: Consulta',
  cuerpo: 'Este mensaje lo envié yo.',
  created_at: '2024-03-10T15:00:00',
}

const mensajeOtro: MensajeRead = {
  id: 'msg-2',
  hilo_id: 'hilo-1',
  remitente_id: 'otro-user-uuid',
  asunto: 'Re: Re',
  cuerpo: 'Este mensaje lo envió otro.',
  created_at: '2024-03-10T15:05:00',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useAuth).mockReturnValue({
    user: { id: CURRENT_USER_ID, email: 'prof@test.com', roles: ['PROFESOR'], tenantId: 't1', name: 'Prof Test' },
    roles: ['PROFESOR'], tenantId: 't1', isAuthenticated: true, isInitializing: false,
    login: vi.fn(), logout: vi.fn(),
  })
  vi.mocked(service.listarHilos).mockResolvedValue([sampleHilo])
  vi.mocked(service.abrirHilo).mockResolvedValue([mensajePropio, mensajeOtro])
})

describe('InboxPage — lista de hilos', () => {
  it('renders the hilos list with asunto', async () => {
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByText('Consulta de notas')).toBeInTheDocument())
  })

  it('shows badge for unread count', async () => {
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByText('2')).toBeInTheDocument())
  })
})

describe('InboxPage — estado vacío', () => {
  it('shows empty state when no hilos', async () => {
    vi.mocked(service.listarHilos).mockResolvedValue([])
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => expect(screen.getByText('Sin mensajes')).toBeInTheDocument())
  })
})

describe('InboxPage — apertura de hilo', () => {
  it('loads messages when a hilo is selected', async () => {
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Consulta de notas'))
    fireEvent.click(screen.getByText('Consulta de notas'))
    await waitFor(() => {
      expect(service.abrirHilo).toHaveBeenCalledWith('hilo-1')
      expect(screen.getByText('Este mensaje lo envié yo.')).toBeInTheDocument()
    })
  })
})

describe('InboxPage — distinción de mensajes propios', () => {
  it('shows "Yo" label for own messages and "Otro" for others', async () => {
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Consulta de notas'))
    fireEvent.click(screen.getByText('Consulta de notas'))
    await waitFor(() => {
      expect(screen.getByText(/Yo ·/)).toBeInTheDocument()
      expect(screen.getByText(/Otro ·/)).toBeInTheDocument()
    })
  })
})

describe('InboxPage — nuevo hilo form', () => {
  it('opens NuevoHiloForm when clicking "Nuevo mensaje"', async () => {
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Nuevo mensaje'))
    fireEvent.click(screen.getByText('Nuevo mensaje'))
    expect(screen.getByText('Nuevo mensaje', { selector: 'h3' })).toBeInTheDocument()
  })

  it('shows domain error on 409 (hilo duplicado)', async () => {
    vi.mocked(service.iniciarHilo).mockRejectedValue({ status: 409, detail: 'HiloDuplicado' })
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Nuevo mensaje'))
    fireEvent.click(screen.getByText('Nuevo mensaje'))

    const destInput = screen.getByPlaceholderText('UUID del destinatario')
    const cuerpoInput = screen.getByPlaceholderText('Escribí tu mensaje...')
    fireEvent.change(destInput, { target: { value: '550e8400-e29b-41d4-a716-446655440000' } })
    fireEvent.change(cuerpoInput, { target: { value: 'Hola' } })

    const submitBtn = screen.getByRole('button', { name: /Enviar/ })
    fireEvent.click(submitBtn)

    await waitFor(() =>
      expect(screen.getByText('Ya existe un hilo de mensajería con este destinatario.')).toBeInTheDocument()
    )
  })

  it('shows domain error on 404 (destinatario inválido)', async () => {
    vi.mocked(service.iniciarHilo).mockRejectedValue({ status: 404, detail: 'DestinatarioInvalido' })
    render(<InboxPage />, { wrapper: makeWrapper() })
    await waitFor(() => screen.getByText('Nuevo mensaje'))
    fireEvent.click(screen.getByText('Nuevo mensaje'))

    fireEvent.change(screen.getByPlaceholderText('UUID del destinatario'), {
      target: { value: '550e8400-e29b-41d4-a716-446655440000' },
    })
    fireEvent.change(screen.getByPlaceholderText('Escribí tu mensaje...'), {
      target: { value: 'Hola' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Enviar/ }))

    await waitFor(() =>
      expect(screen.getByText('El destinatario no existe en este tenant.')).toBeInTheDocument()
    )
  })
})
