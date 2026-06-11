/**
 * Tests for perfilService — stubs the transport (axios-mock-adapter).
 * Covers GET /perfil and PATCH /perfil with success + error cases (409, 422).
 * Identity (id/cuil/legajo) never travels in the PATCH body — that is the contract.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import { getPerfil, updatePerfil } from '../perfilService'
import type { PerfilRead } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

afterEach(() => {
  mock.reset()
})

const samplePerfil: PerfilRead = {
  id: 'u-1',
  email: 'docente@test.com',
  nombre: 'Ana',
  apellidos: 'Gómez',
  dni: '30111222',
  cuil: '27-30111222-4',
  cbu: '0110599520000001234567',
  alias_cbu: 'ana.gomez.cbu',
  genero: 'F',
  legajo: 'L-001',
  legajo_profesional: 'MP-1234',
  banco: 'Nación',
  regional: 'BUE',
  facturador: true,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-06-01T00:00:00',
}

describe('getPerfil', () => {
  it('returns PerfilRead on 200', async () => {
    mock.onGet('/perfil').reply(200, samplePerfil)
    const result = await getPerfil()
    expect(result).toEqual(samplePerfil)
  })

  it('throws DomainError on 401 (no session)', async () => {
    mock.onGet('/perfil').reply(401, { detail: 'No autenticado' })
    await expect(getPerfil()).rejects.toMatchObject({ status: 401 })
  })
})

describe('updatePerfil', () => {
  it('returns updated PerfilRead on 200', async () => {
    const updated = { ...samplePerfil, nombre: 'Ana María' }
    mock.onPatch('/perfil').reply(200, updated)
    const result = await updatePerfil({ nombre: 'Ana María' })
    expect(result).toEqual(updated)
  })

  it('sends only the provided editable fields in the body (no identity)', async () => {
    mock.onPatch('/perfil').reply(200, samplePerfil)
    await updatePerfil({ nombre: 'Ana', email: 'nuevo@test.com', facturador: false })
    const sentBody = JSON.parse(mock.history.patch[0].data as string)
    expect(Object.keys(sentBody).sort()).toEqual(['email', 'facturador', 'nombre'])
    expect(sentBody).not.toHaveProperty('id')
    expect(sentBody).not.toHaveProperty('cuil')
    expect(sentBody).not.toHaveProperty('legajo')
  })

  it('throws DomainError on 409 (email duplicado en el tenant)', async () => {
    mock.onPatch('/perfil').reply(409, { detail: 'email ya usado en el tenant' })
    await expect(updatePerfil({ email: 'dup@test.com' })).rejects.toMatchObject({
      status: 409,
      detail: 'email ya usado en el tenant',
    })
  })

  it('throws DomainError on 422 (validación)', async () => {
    mock.onPatch('/perfil').reply(422, { detail: 'email no válido' })
    await expect(updatePerfil({ email: 'bad' })).rejects.toMatchObject({ status: 422 })
  })

  it('throws DomainError on 403 (sin permiso perfil:editar)', async () => {
    mock.onPatch('/perfil').reply(403, { detail: 'sin permiso' })
    await expect(updatePerfil({ nombre: 'X' })).rejects.toMatchObject({ status: 403 })
  })
})
