/**
 * Tests for comunicacionService — stubs transport via axios-mock-adapter.
 * Covers preview, encolar, getLote, aprobarLote, cancelarLote, aprobarIndividual, cancelarIndividual.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  previewComunicacion,
  encolarLote,
  getLote,
  aprobarLote,
  cancelarLote,
  aprobarIndividual,
  cancelarIndividual,
  getMisEnvios,
} from '../comunicacionService'
import type { ComunicacionRead, LoteStatusResponse, MisEnviosResponse } from '../../types'

let mock: MockAdapter

beforeEach(() => { mock = new MockAdapter(apiClient) })
afterEach(() => { mock.reset() })

const sampleMsg: ComunicacionRead = {
  id: 'msg1', lote_id: 'lote1', destinatario_email: 'a@t.com',
  asunto: 'Hola', cuerpo: 'Texto', estado: 'Pendiente',
  creado_en: '2026-06-05', actualizado_en: '2026-06-05',
}

const sampleLote: LoteStatusResponse = {
  lote_id: 'lote1', mensajes: [sampleMsg],
  pendientes: 1, enviados: 0, fallidos: 0, cancelados: 0,
}

describe('previewComunicacion', () => {
  it('returns rendered asunto and cuerpo on 200', async () => {
    mock.onPost('/comunicaciones/preview').reply(200, { asunto: 'Hola Ana', cuerpo: 'Texto renderizado' })
    const result = await previewComunicacion({
      asunto_plantilla: 'Hola {{nombre}}',
      cuerpo_plantilla: 'Texto renderizado',
      variables: { nombre: 'Ana' },
    })
    expect(result.asunto).toBe('Hola Ana')
    expect(result.cuerpo).toBe('Texto renderizado')
  })

  it('throws DomainError on 422 (missing variable)', async () => {
    mock.onPost('/comunicaciones/preview').reply(422, { detail: 'variable {{nombre}} no resuelta' })
    await expect(previewComunicacion({
      asunto_plantilla: 'Hola {{nombre}}',
      cuerpo_plantilla: 'Texto',
      variables: {},
    })).rejects.toMatchObject({ status: 422, detail: 'variable {{nombre}} no resuelta' })
  })
})

describe('encolarLote', () => {
  it('returns lote_id and total_encolados on 201', async () => {
    mock.onPost('/comunicaciones/encolar').reply(201, { lote_id: 'lote1', total_encolados: 2 })
    const result = await encolarLote({
      destinatarios: ['a@t.com'],
      asunto_plantilla: 'Hola',
      cuerpo_plantilla: 'Texto',
      variables_por_destinatario: { 'a@t.com': {} },
    })
    expect(result.lote_id).toBe('lote1')
    expect(result.total_encolados).toBe(2)
  })

  it('does NOT include identity or tenant in the request body', async () => {
    mock.onPost('/comunicaciones/encolar').reply(201, { lote_id: 'lote1', total_encolados: 1 })
    await encolarLote({
      destinatarios: ['a@t.com'],
      asunto_plantilla: 'Hola',
      cuerpo_plantilla: 'Texto',
      variables_por_destinatario: { 'a@t.com': {} },
    })
    const sentBody = JSON.parse(mock.history.post[0].data as string)
    expect(sentBody).not.toHaveProperty('user_id')
    expect(sentBody).not.toHaveProperty('tenant_id')
    expect(sentBody).not.toHaveProperty('remitente_id')
    expect(Object.keys(sentBody)).toEqual(
      expect.arrayContaining(['destinatarios', 'asunto_plantilla', 'cuerpo_plantilla', 'variables_por_destinatario']),
    )
  })

  it('throws DomainError on 422', async () => {
    mock.onPost('/comunicaciones/encolar').reply(422, { detail: 'sin destinatarios' })
    await expect(encolarLote({
      destinatarios: [],
      asunto_plantilla: 'Hola',
      cuerpo_plantilla: 'Texto',
      variables_por_destinatario: {},
    })).rejects.toMatchObject({ status: 422 })
  })
})

describe('getLote', () => {
  it('returns LoteStatusResponse on 200', async () => {
    mock.onGet('/comunicaciones/lote/lote1').reply(200, sampleLote)
    const result = await getLote('lote1')
    expect(result.lote_id).toBe('lote1')
    expect(result.mensajes).toHaveLength(1)
  })

  it('throws DomainError on 404', async () => {
    mock.onGet('/comunicaciones/lote/bad').reply(404, { detail: 'lote no encontrado' })
    await expect(getLote('bad')).rejects.toMatchObject({ status: 404 })
  })
})

describe('aprobarLote / cancelarLote', () => {
  it('aprobarLote returns updated messages on 200', async () => {
    mock.onPost('/comunicaciones/aprobar-lote').reply(200, [{ ...sampleMsg, estado: 'Enviando' }])
    const result = await aprobarLote('lote1')
    expect(result[0].estado).toBe('Enviando')
  })

  it('cancelarLote throws DomainError on 409 (invalid transition)', async () => {
    mock.onPost('/comunicaciones/cancelar-lote').reply(409, { detail: 'transicion invalida' })
    await expect(cancelarLote('lote1')).rejects.toMatchObject({ status: 409 })
  })
})

describe('aprobarIndividual / cancelarIndividual', () => {
  it('aprobarIndividual returns updated message on 200', async () => {
    mock.onPost('/comunicaciones/aprobar-individual').reply(200, { ...sampleMsg, estado: 'Enviando' })
    const result = await aprobarIndividual('msg1')
    expect(result.estado).toBe('Enviando')
  })

  it('cancelarIndividual throws DomainError on 404', async () => {
    mock.onPost('/comunicaciones/cancelar-individual').reply(404, { detail: 'mensaje no encontrado' })
    await expect(cancelarIndividual('msg1')).rejects.toMatchObject({ status: 404 })
  })
})

// C-27 — getMisEnvios
describe('getMisEnvios', () => {
  const sampleMisEnvios: MisEnviosResponse = {
    total: 2,
    offset: 0,
    limit: 20,
    items: [sampleMsg, { ...sampleMsg, id: 'msg2' }],
  }

  it('returns MisEnviosResponse on 200 without params', async () => {
    mock.onGet('/comunicaciones/mis-envios').reply(200, sampleMisEnvios)
    const result = await getMisEnvios()
    expect(result.total).toBe(2)
    expect(result.items).toHaveLength(2)
  })

  it('serializes estado filter as query param', async () => {
    mock.onGet('/comunicaciones/mis-envios').reply(200, { ...sampleMisEnvios, total: 1, items: [sampleMsg] })
    const result = await getMisEnvios({ estado: 'Enviado', offset: 0, limit: 20 })
    expect(result.total).toBe(1)
    // Verify the params were sent
    const request = mock.history.get[0]
    expect(request.params).toMatchObject({ estado: 'Enviado', offset: 0, limit: 20 })
  })

  it('returns empty list when no envíos', async () => {
    mock.onGet('/comunicaciones/mis-envios').reply(200, { total: 0, offset: 0, limit: 20, items: [] })
    const result = await getMisEnvios()
    expect(result.total).toBe(0)
    expect(result.items).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/comunicaciones/mis-envios').reply(403, { detail: 'forbidden' })
    await expect(getMisEnvios()).rejects.toMatchObject({ status: 403 })
  })
})
