/**
 * Tests for asignacionService — stubs the transport (axios-mock-adapter).
 * Covers GET /asignaciones, POST /asignaciones, PATCH /asignaciones/{id},
 * DELETE /asignaciones/{id} with success + error cases.
 * Identity (tenant_id) never travels in the body — that is the contract.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarAsignaciones,
  crearAsignacion,
  editarAsignacion,
  darBajaAsignacion,
} from '../asignacionService'
import type { AsignacionRead, AsignacionCreate, AsignacionUpdate } from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})

afterEach(() => {
  mock.reset()
})

const sampleAsignacion: AsignacionRead = {
  id: 'asgn-1',
  usuario_id: 'user-1',
  rol: 'PROFESOR',
  desde: '2026-03-01',
  hasta: null,
  materia_id: 'mat-1',
  carrera_id: 'car-1',
  cohorte_id: 'coh-1',
  comisiones: [],
  responsable_id: null,
  estado_vigencia: 'vigente',
  created_at: '2026-03-01T10:00:00',
  updated_at: '2026-03-01T10:00:00',
}

const validCreate: AsignacionCreate = {
  usuario_id: 'user-1',
  rol: 'PROFESOR',
  desde: '2026-03-01',
}

const validUpdate: AsignacionUpdate = {
  rol: 'TUTOR',
}

// ── listarAsignaciones ──────────────────────────────────────────────────────

describe('listarAsignaciones', () => {
  it('returns AsignacionRead[] on 200 with no filters', async () => {
    mock.onGet('/asignaciones').reply(200, [sampleAsignacion])
    const result = await listarAsignaciones({})
    expect(result).toEqual([sampleAsignacion])
  })

  it('forwards provided filters as query params and omits nullish ones', async () => {
    mock.onGet('/asignaciones').reply(200, [sampleAsignacion])
    await listarAsignaciones({ rol: 'PROFESOR', usuario_id: 'user-1' })
    const sentParams = mock.history.get[0].params as Record<string, string>
    expect(sentParams).toEqual({ rol: 'PROFESOR', usuario_id: 'user-1' })
    expect(sentParams).not.toHaveProperty('responsable_id')
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/asignaciones').reply(403, { detail: 'sin permiso equipos:asignar' })
    await expect(listarAsignaciones({})).rejects.toMatchObject({ status: 403 })
  })

  it('returns empty array on 200 with empty list', async () => {
    mock.onGet('/asignaciones').reply(200, [])
    const result = await listarAsignaciones({})
    expect(result).toEqual([])
  })
})

// ── crearAsignacion ─────────────────────────────────────────────────────────

describe('crearAsignacion', () => {
  it('returns AsignacionRead on 201', async () => {
    mock.onPost('/asignaciones').reply(201, sampleAsignacion)
    const result = await crearAsignacion(validCreate)
    expect(result).toEqual(sampleAsignacion)
  })

  it('sends usuario_id, rol, desde and never tenant_id', async () => {
    mock.onPost('/asignaciones').reply(201, sampleAsignacion)
    await crearAsignacion(validCreate)
    const sentBody = JSON.parse(mock.history.post[0].data as string) as Record<string, unknown>
    expect(sentBody).toMatchObject(validCreate)
    expect(sentBody).not.toHaveProperty('tenant_id')
  })

  it('throws DomainError on 422 (usuario no encontrado)', async () => {
    mock.onPost('/asignaciones').reply(422, { detail: 'Usuario no encontrado' })
    await expect(crearAsignacion(validCreate)).rejects.toMatchObject({ status: 422 })
  })

  it('throws DomainError on 403 (sin permiso)', async () => {
    mock.onPost('/asignaciones').reply(403, { detail: 'sin permiso' })
    await expect(crearAsignacion(validCreate)).rejects.toMatchObject({ status: 403 })
  })
})

// ── editarAsignacion ────────────────────────────────────────────────────────

describe('editarAsignacion', () => {
  it('returns updated AsignacionRead on 200', async () => {
    const updated = { ...sampleAsignacion, rol: 'TUTOR' as const }
    mock.onPatch('/asignaciones/asgn-1').reply(200, updated)
    const result = await editarAsignacion('asgn-1', validUpdate)
    expect(result.rol).toBe('TUTOR')
  })

  it('sends only the provided patch fields', async () => {
    mock.onPatch('/asignaciones/asgn-1').reply(200, sampleAsignacion)
    await editarAsignacion('asgn-1', { rol: 'TUTOR' })
    const sentBody = JSON.parse(mock.history.patch[0].data as string) as Record<string, unknown>
    expect(sentBody).toEqual({ rol: 'TUTOR' })
  })

  it('throws DomainError on 404 (asignacion no encontrada)', async () => {
    mock.onPatch('/asignaciones/not-found').reply(404, { detail: 'Asignacion no encontrada' })
    await expect(editarAsignacion('not-found', validUpdate)).rejects.toMatchObject({ status: 404 })
  })

  it('throws DomainError on 422 (referencia invalida)', async () => {
    mock.onPatch('/asignaciones/asgn-1').reply(422, { detail: 'Referencia invalida' })
    await expect(editarAsignacion('asgn-1', validUpdate)).rejects.toMatchObject({ status: 422 })
  })
})

// ── darBajaAsignacion ───────────────────────────────────────────────────────

describe('darBajaAsignacion', () => {
  it('resolves with undefined on 204', async () => {
    mock.onDelete('/asignaciones/asgn-1').reply(204)
    const result = await darBajaAsignacion('asgn-1')
    expect(result).toBeUndefined()
  })

  it('throws DomainError on 404 (asignacion no encontrada)', async () => {
    mock.onDelete('/asignaciones/not-found').reply(404, { detail: 'Asignacion no encontrada' })
    await expect(darBajaAsignacion('not-found')).rejects.toMatchObject({ status: 404 })
  })

  it('throws DomainError on 403 (sin permiso)', async () => {
    mock.onDelete('/asignaciones/asgn-1').reply(403, { detail: 'sin permiso' })
    await expect(darBajaAsignacion('asgn-1')).rejects.toMatchObject({ status: 403 })
  })
})
