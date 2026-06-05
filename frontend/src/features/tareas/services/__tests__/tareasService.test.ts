/**
 * Tests for tareasService — stubs transport via axios-mock-adapter.
 * TDD: RED first (service not yet implemented), then GREEN.
 * Covers tasks 3.2, 3.3, 3.4:
 *   - GET /tareas/mias, GET /tareas/{id}, GET /tareas/admin (with filters)
 *   - POST /tareas (alta), POST /tareas/{id}/delegar
 *   - PATCH /tareas/{id}/estado, GET/POST /tareas/{id}/comentarios
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarMias,
  detalleTarea,
  listarAdmin,
  crearTarea,
  delegarTarea,
  cambiarEstado,
  listarComentarios,
  agregarComentario,
} from '../tareasService'
import type {
  TareaRead,
  ComentarioTareaRead,
  TareaCreateRequest,
  TareaDelegarRequest,
  TareaUpdateEstadoRequest,
  ComentarioTareaCreateRequest,
  TareasAdminParams,
} from '../../types'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(apiClient)
})
afterEach(() => {
  mock.reset()
})

const sampleTarea: TareaRead = {
  id: 'tarea-1',
  tenant_id: 'tenant-1',
  asignado_a: 'user-1',
  asignado_por: 'coord-1',
  descripcion: 'Revisar actas del coloquio',
  estado: 'Pendiente',
  materia_id: 'mat-1',
  contexto_id: null,
  contexto_tipo: null,
  created_at: '2024-06-01T10:00:00Z',
  updated_at: '2024-06-01T10:00:00Z',
  deleted_at: null,
}

const sampleComentario: ComentarioTareaRead = {
  id: 'com-1',
  tenant_id: 'tenant-1',
  tarea_id: 'tarea-1',
  autor_id: 'user-1',
  cuerpo: 'Entendido, lo reviso hoy',
  es_sistema: false,
  created_at: '2024-06-01T11:00:00Z',
  updated_at: '2024-06-01T11:00:00Z',
  deleted_at: null,
}

// ---------------------------------------------------------------------------
// Task 3.2 — listarMias
// ---------------------------------------------------------------------------
describe('listarMias', () => {
  it('returns list of tasks on 200', async () => {
    mock.onGet('/tareas/mias').reply(200, [sampleTarea])
    const result = await listarMias()
    expect(result).toEqual([sampleTarea])
    expect(result[0].estado).toBe('Pendiente')
  })

  it('returns empty array on 200 with no tasks', async () => {
    mock.onGet('/tareas/mias').reply(200, [])
    const result = await listarMias()
    expect(result).toEqual([])
  })

  it('throws DomainError on 401 (unauthenticated)', async () => {
    mock.onGet('/tareas/mias').reply(401, { detail: 'Unauthorized' })
    await expect(listarMias()).rejects.toMatchObject({ status: 401 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.2 — detalleTarea
// ---------------------------------------------------------------------------
describe('detalleTarea', () => {
  it('returns tarea on 200', async () => {
    mock.onGet('/tareas/tarea-1').reply(200, sampleTarea)
    const result = await detalleTarea('tarea-1')
    expect(result).toEqual(sampleTarea)
  })

  it('throws DomainError on 404 (not found)', async () => {
    mock.onGet('/tareas/tarea-99').reply(404, { detail: 'Tarea no encontrada' })
    await expect(detalleTarea('tarea-99')).rejects.toMatchObject({ status: 404, detail: 'Tarea no encontrada' })
  })

  it('throws DomainError on 403 (forbidden)', async () => {
    mock.onGet('/tareas/tarea-other').reply(403, { detail: 'Forbidden' })
    await expect(detalleTarea('tarea-other')).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.2 — listarAdmin
// ---------------------------------------------------------------------------
describe('listarAdmin', () => {
  it('returns list with no filters on 200', async () => {
    mock.onGet('/tareas/admin').reply(200, [sampleTarea])
    const result = await listarAdmin({})
    expect(result).toEqual([sampleTarea])
  })

  it('passes all filters as query params', async () => {
    mock.onGet('/tareas/admin').reply(200, [sampleTarea])
    const params: TareasAdminParams = {
      asignado_a: 'user-1',
      materia_id: 'mat-1',
      estado: 'EnProgreso',
      q: 'coloquio',
    }
    await listarAdmin(params)
    const sentParams = mock.history.get[0].params
    expect(sentParams).toMatchObject({
      asignado_a: 'user-1',
      materia_id: 'mat-1',
      estado: 'EnProgreso',
      q: 'coloquio',
    })
  })

  it('omits null/undefined filter params from the request', async () => {
    mock.onGet('/tareas/admin').reply(200, [])
    await listarAdmin({ asignado_a: null, estado: null })
    const sentParams = mock.history.get[0].params ?? {}
    expect(sentParams).not.toHaveProperty('asignado_a')
    expect(sentParams).not.toHaveProperty('estado')
  })

  it('throws DomainError on 403 (no tareas:gestionar)', async () => {
    mock.onGet('/tareas/admin').reply(403, { detail: 'Forbidden' })
    await expect(listarAdmin({})).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.3 — crearTarea
// ---------------------------------------------------------------------------
describe('crearTarea', () => {
  const body: TareaCreateRequest = {
    asignado_a: 'user-1',
    descripcion: 'Revisar actas',
  }

  it('returns TareaRead on 201', async () => {
    mock.onPost('/tareas').reply(201, sampleTarea)
    const result = await crearTarea(body)
    expect(result).toEqual(sampleTarea)
    expect(result.estado).toBe('Pendiente')
  })

  it('throws DomainError on 422 (validation error)', async () => {
    mock.onPost('/tareas').reply(422, { detail: [{ msg: 'descripcion too short', loc: ['body', 'descripcion'] }] })
    await expect(crearTarea({ asignado_a: 'u1', descripcion: '' })).rejects.toMatchObject({ status: 422 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.3 — delegarTarea
// ---------------------------------------------------------------------------
describe('delegarTarea', () => {
  const body: TareaDelegarRequest = { asignado_a: 'user-2' }

  it('returns updated TareaRead on 200', async () => {
    const delegated = { ...sampleTarea, asignado_a: 'user-2' }
    mock.onPost('/tareas/tarea-1/delegar').reply(200, delegated)
    const result = await delegarTarea('tarea-1', body)
    expect(result.asignado_a).toBe('user-2')
  })

  it('throws DomainError on 404 (tarea not found)', async () => {
    mock.onPost('/tareas/tarea-99/delegar').reply(404, { detail: 'Tarea no encontrada' })
    await expect(delegarTarea('tarea-99', body)).rejects.toMatchObject({ status: 404 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.4 — cambiarEstado
// ---------------------------------------------------------------------------
describe('cambiarEstado', () => {
  const body: TareaUpdateEstadoRequest = { estado: 'EnProgreso' }

  it('returns updated tarea on 200', async () => {
    const updated = { ...sampleTarea, estado: 'EnProgreso' as const }
    mock.onPatch('/tareas/tarea-1/estado').reply(200, updated)
    const result = await cambiarEstado('tarea-1', body)
    expect(result.estado).toBe('EnProgreso')
  })

  it('throws DomainError on 422 (invalid transition — e.g. Cancelada → EnProgreso)', async () => {
    mock.onPatch('/tareas/tarea-1/estado').reply(422, { detail: 'Transición no permitida' })
    await expect(cambiarEstado('tarea-1', { estado: 'EnProgreso' })).rejects.toMatchObject({
      status: 422,
      detail: 'Transición no permitida',
    })
  })

  it('throws DomainError on 403 (forbidden)', async () => {
    mock.onPatch('/tareas/tarea-2/estado').reply(403, { detail: 'Forbidden' })
    await expect(cambiarEstado('tarea-2', body)).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.4 — listarComentarios
// ---------------------------------------------------------------------------
describe('listarComentarios', () => {
  it('returns list of comments on 200', async () => {
    mock.onGet('/tareas/tarea-1/comentarios').reply(200, [sampleComentario])
    const result = await listarComentarios('tarea-1')
    expect(result).toEqual([sampleComentario])
    expect(result[0].es_sistema).toBe(false)
  })

  it('returns empty array when no comments exist', async () => {
    mock.onGet('/tareas/tarea-1/comentarios').reply(200, [])
    const result = await listarComentarios('tarea-1')
    expect(result).toEqual([])
  })

  it('throws DomainError on 404', async () => {
    mock.onGet('/tareas/tarea-99/comentarios').reply(404, { detail: 'Tarea no encontrada' })
    await expect(listarComentarios('tarea-99')).rejects.toMatchObject({ status: 404 })
  })
})

// ---------------------------------------------------------------------------
// Task 3.4 — agregarComentario
// ---------------------------------------------------------------------------
describe('agregarComentario', () => {
  const body: ComentarioTareaCreateRequest = { cuerpo: 'Entendido' }

  it('returns ComentarioTareaRead on 201', async () => {
    mock.onPost('/tareas/tarea-1/comentarios').reply(201, sampleComentario)
    const result = await agregarComentario('tarea-1', body)
    expect(result).toEqual(sampleComentario)
    expect(result.tarea_id).toBe('tarea-1')
  })

  it('throws DomainError on 403 (not owner or gestionar)', async () => {
    mock.onPost('/tareas/tarea-1/comentarios').reply(403, { detail: 'Forbidden' })
    await expect(agregarComentario('tarea-1', body)).rejects.toMatchObject({ status: 403 })
  })
})
