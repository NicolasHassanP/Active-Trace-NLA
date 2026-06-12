/**
 * Tests for usuarioAdminService — stubs transport (axios-mock-adapter).
 * Covers GET/POST/PATCH/DELETE for admin/usuarios.
 * Contracts:
 *   - tenant_id NEVER in request body
 *   - 409 ConflictoEmail → DomainError { status: 409 }
 *   - 404 UsuarioNoEncontrado → DomainError { status: 404 }
 *   - 403 → DomainError { status: 403 }
 *   - Identity NEVER in body (rule #8)
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarUsuarios,
  crearUsuario,
  editarUsuario,
  darBajaUsuario,
} from '../usuarioAdminService'
import type { UsuarioRead, UsuarioCreate } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

afterEach(() => {
  mock.reset()
})

// ── Fixtures ─────────────────────────────────────────────────────────────────

const sampleUsuario: UsuarioRead = {
  id: 'usr-uuid-1',
  email: 'admin@test.com',
  nombre: 'Ana',
  apellidos: 'García',
  legajo: 'LEG001',
  estado: 'activo',
  asignaciones: [],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

// ── listarUsuarios ────────────────────────────────────────────────────────────

describe('listarUsuarios', () => {
  it('returns UsuarioRead[] on 200', async () => {
    mock.onGet('/admin/usuarios').reply(200, [sampleUsuario])
    const result = await listarUsuarios()
    expect(result).toEqual([sampleUsuario])
  })

  it('returns empty array on 200 with no items', async () => {
    mock.onGet('/admin/usuarios').reply(200, [])
    const result = await listarUsuarios()
    expect(result).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/admin/usuarios').reply(403, { detail: 'sin permiso usuarios:gestionar' })
    await expect(listarUsuarios()).rejects.toMatchObject({ status: 403 })
  })
})

// ── crearUsuario ──────────────────────────────────────────────────────────────

describe('crearUsuario', () => {
  const body: UsuarioCreate = {
    email: 'nuevo@test.com',
    nombre: 'Pedro',
    apellidos: 'López',
  }

  it('returns UsuarioRead on 201', async () => {
    mock.onPost('/admin/usuarios').reply(201, sampleUsuario)
    const result = await crearUsuario(body)
    expect(result).toEqual(sampleUsuario)
  })

  it('sends email, nombre, apellidos; never tenant_id', async () => {
    mock.onPost('/admin/usuarios').reply(201, sampleUsuario)
    await crearUsuario(body)
    const sent = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sent).toMatchObject(body)
    expect(sent).not.toHaveProperty('tenant_id')
  })

  it('never sends PII fields (dni/cuil/cbu/alias_cbu)', async () => {
    mock.onPost('/admin/usuarios').reply(201, sampleUsuario)
    await crearUsuario(body)
    const sent = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sent).not.toHaveProperty('dni')
    expect(sent).not.toHaveProperty('cuil')
    expect(sent).not.toHaveProperty('cbu')
    expect(sent).not.toHaveProperty('alias_cbu')
  })

  it('throws DomainError on 409 (ConflictoEmail)', async () => {
    mock.onPost('/admin/usuarios').reply(409, { detail: 'ConflictoEmail: email ya registrado' })
    await expect(crearUsuario(body)).rejects.toMatchObject({ status: 409 })
  })

  it('throws DomainError on 403', async () => {
    mock.onPost('/admin/usuarios').reply(403, { detail: 'sin permiso' })
    await expect(crearUsuario(body)).rejects.toMatchObject({ status: 403 })
  })
})

// ── editarUsuario ─────────────────────────────────────────────────────────────

describe('editarUsuario', () => {
  it('returns updated UsuarioRead on 200', async () => {
    const updated = { ...sampleUsuario, nombre: 'Ana Maria' }
    mock.onPatch('/admin/usuarios/usr-uuid-1').reply(200, updated)
    const result = await editarUsuario('usr-uuid-1', { nombre: 'Ana Maria' })
    expect(result.nombre).toBe('Ana Maria')
  })

  it('throws DomainError on 409 (ConflictoEmail)', async () => {
    mock.onPatch('/admin/usuarios/usr-uuid-1').reply(409, { detail: 'ConflictoEmail' })
    await expect(editarUsuario('usr-uuid-1', { email: 'otro@test.com' })).rejects.toMatchObject({ status: 409 })
  })

  it('throws DomainError on 404 (UsuarioNoEncontrado)', async () => {
    mock.onPatch('/admin/usuarios/no-existe').reply(404, { detail: 'Usuario no encontrado' })
    await expect(editarUsuario('no-existe', { nombre: 'X' })).rejects.toMatchObject({ status: 404 })
  })

  it('never sends tenant_id in the body', async () => {
    mock.onPatch('/admin/usuarios/usr-uuid-1').reply(200, sampleUsuario)
    await editarUsuario('usr-uuid-1', { nombre: 'Test' })
    const sent = JSON.parse(mock.history.patch[0].data as string) as Record<string, unknown>
    expect(sent).not.toHaveProperty('tenant_id')
  })
})

// ── darBajaUsuario ────────────────────────────────────────────────────────────

describe('darBajaUsuario', () => {
  it('resolves undefined on 204', async () => {
    mock.onDelete('/admin/usuarios/usr-uuid-1').reply(204)
    const result = await darBajaUsuario('usr-uuid-1')
    expect(result).toBeUndefined()
  })

  it('throws DomainError on 404', async () => {
    mock.onDelete('/admin/usuarios/no-existe').reply(404, { detail: 'Usuario no encontrado' })
    await expect(darBajaUsuario('no-existe')).rejects.toMatchObject({ status: 404 })
  })

  it('throws DomainError on 403', async () => {
    mock.onDelete('/admin/usuarios/usr-uuid-1').reply(403, { detail: 'sin permiso' })
    await expect(darBajaUsuario('usr-uuid-1')).rejects.toMatchObject({ status: 403 })
  })
})
