/**
 * Tests for inboxUsuariosService — stubs transport via axios-mock-adapter.
 * Verifies: correct endpoint (/inbox/usuarios), q param forwarding,
 * tenant/identity never in request, error propagation.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { buscarUsuariosInbox } from '../inboxUsuariosService'
import type { UsuarioAsignable } from '@/features/asignaciones/types'

let mock: MockAdapter
beforeEach(() => { mock = new MockAdapter(apiClient) })
afterEach(() => { mock.reset() })

const sampleUsuario: UsuarioAsignable = {
  id: 'user-1',
  nombre: 'Ana',
  apellidos: 'García',
  email: 'ana@test.com',
  legajo: 'L-100',
}

describe('buscarUsuariosInbox', () => {
  it('calls GET /inbox/usuarios with q param and returns users', async () => {
    mock.onGet('/inbox/usuarios', { params: { q: 'ana' } }).reply(200, [sampleUsuario])
    const result = await buscarUsuariosInbox('ana')
    expect(result).toEqual([sampleUsuario])
  })

  it('calls GET /inbox/usuarios without params when q is empty', async () => {
    mock.onGet('/inbox/usuarios').reply(200, [sampleUsuario])
    const result = await buscarUsuariosInbox('')
    expect(result).toEqual([sampleUsuario])
  })

  it('does NOT include tenant_id or identity in the request', async () => {
    let capturedParams: Record<string, unknown> = {}
    mock.onGet('/inbox/usuarios').reply((config) => {
      capturedParams = (config.params ?? {}) as Record<string, unknown>
      return [200, []]
    })
    await buscarUsuariosInbox('test')
    expect(capturedParams).not.toHaveProperty('tenant_id')
    expect(capturedParams).not.toHaveProperty('usuario_id')
  })

  it('trims whitespace from q before sending', async () => {
    mock.onGet('/inbox/usuarios', { params: { q: 'ana' } }).reply(200, [sampleUsuario])
    const result = await buscarUsuariosInbox('  ana  ')
    expect(result).toEqual([sampleUsuario])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/inbox/usuarios').reply(403, { detail: 'Forbidden' })
    await expect(buscarUsuariosInbox('x')).rejects.toMatchObject({ status: 403 })
  })

  it('returns empty array when no users match', async () => {
    mock.onGet('/inbox/usuarios', { params: { q: 'zzz' } }).reply(200, [])
    const result = await buscarUsuariosInbox('zzz')
    expect(result).toEqual([])
  })
})
