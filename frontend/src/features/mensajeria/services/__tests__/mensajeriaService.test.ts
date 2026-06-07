/**
 * Tests for mensajeriaService — stubs transport via axios-mock-adapter.
 * Task 7.1: cada función llama al endpoint correcto; identidad/tenant nunca en el body.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import apiClient from '@/shared/services/api'
import {
  listarHilos,
  abrirHilo,
  iniciarHilo,
  responder,
} from '../mensajeriaService'
import type { InboxHiloRead, MensajeRead } from '../../types'

let mock: MockAdapter
beforeEach(() => { mock = new MockAdapter(apiClient) })
afterEach(() => { mock.reset() })

const sampleHilo: InboxHiloRead = {
  id: 'hilo-1',
  asunto: 'Consulta de notas',
  no_leidos: 2,
  ultimo_mensaje_at: '2024-03-10T15:00:00',
}

const sampleMensaje: MensajeRead = {
  id: 'msg-1',
  hilo_id: 'hilo-1',
  remitente_id: 'user-abc',
  asunto: 'Re: Consulta',
  cuerpo: 'Hola, las notas están en el sistema.',
  created_at: '2024-03-10T15:00:00',
}

// ---------------------------------------------------------------------------
// listarHilos
// ---------------------------------------------------------------------------
describe('listarHilos', () => {
  it('calls GET /inbox and returns hilo list', async () => {
    mock.onGet('/inbox').reply(200, [sampleHilo])
    const result = await listarHilos()
    expect(result).toEqual([sampleHilo])
  })

  it('returns empty array when inbox is empty', async () => {
    mock.onGet('/inbox').reply(200, [])
    const result = await listarHilos()
    expect(result).toEqual([])
  })

  it('throws DomainError on 403', async () => {
    mock.onGet('/inbox').reply(403, { detail: 'Forbidden' })
    await expect(listarHilos()).rejects.toMatchObject({ status: 403 })
  })
})

// ---------------------------------------------------------------------------
// abrirHilo
// ---------------------------------------------------------------------------
describe('abrirHilo', () => {
  it('calls GET /inbox/{hilo_id} and returns mensajes', async () => {
    mock.onGet('/inbox/hilo-1').reply(200, [sampleMensaje])
    const result = await abrirHilo('hilo-1')
    expect(result).toEqual([sampleMensaje])
  })

  it('throws DomainError on 404 (hilo no encontrado)', async () => {
    mock.onGet('/inbox/no-existe').reply(404, { detail: 'HiloNoEncontrado' })
    await expect(abrirHilo('no-existe')).rejects.toMatchObject({ status: 404 })
  })
})

// ---------------------------------------------------------------------------
// iniciarHilo — identidad/tenant NUNCA en el body
// ---------------------------------------------------------------------------
describe('iniciarHilo', () => {
  it('calls POST /inbox with destinatario_id and cuerpo, returns MensajeRead', async () => {
    mock.onPost('/inbox').reply(201, sampleMensaje)
    const result = await iniciarHilo({
      destinatario_id: 'dest-uuid',
      cuerpo: 'Hola!',
    })
    expect(result).toEqual(sampleMensaje)
  })

  it('does NOT include remitente_id or tenant_id in the body', async () => {
    let capturedBody: Record<string, unknown> = {}
    mock.onPost('/inbox').reply((config) => {
      capturedBody = JSON.parse(config.data as string) as Record<string, unknown>
      return [201, sampleMensaje]
    })
    await iniciarHilo({ destinatario_id: 'dest-uuid', cuerpo: 'Hola!' })
    expect(capturedBody).not.toHaveProperty('remitente_id')
    expect(capturedBody).not.toHaveProperty('tenant_id')
  })

  it('throws DomainError on 404 (destinatario inválido)', async () => {
    mock.onPost('/inbox').reply(404, { detail: 'DestinatarioInvalido' })
    await expect(iniciarHilo({ destinatario_id: 'bad-uuid', cuerpo: 'Hola' })).rejects.toMatchObject({ status: 404 })
  })

  it('throws DomainError on 409 (hilo duplicado)', async () => {
    mock.onPost('/inbox').reply(409, { detail: 'HiloDuplicado' })
    await expect(iniciarHilo({ destinatario_id: 'dest-uuid', cuerpo: 'Hola' })).rejects.toMatchObject({ status: 409 })
  })
})

// ---------------------------------------------------------------------------
// responder — identidad/tenant NUNCA en el body
// ---------------------------------------------------------------------------
describe('responder', () => {
  it('calls POST /inbox/{hilo_id}/responder and returns MensajeRead', async () => {
    mock.onPost('/inbox/hilo-1/responder').reply(201, sampleMensaje)
    const result = await responder('hilo-1', { asunto: 'Re: algo', cuerpo: 'Aquí va la respuesta.' })
    expect(result).toEqual(sampleMensaje)
  })

  it('does NOT include remitente_id or tenant_id in the body', async () => {
    let capturedBody: Record<string, unknown> = {}
    mock.onPost('/inbox/hilo-1/responder').reply((config) => {
      capturedBody = JSON.parse(config.data as string) as Record<string, unknown>
      return [201, sampleMensaje]
    })
    await responder('hilo-1', { asunto: 'Re', cuerpo: 'Ok' })
    expect(capturedBody).not.toHaveProperty('remitente_id')
    expect(capturedBody).not.toHaveProperty('tenant_id')
  })

  it('throws DomainError on 404 (hilo no encontrado)', async () => {
    mock.onPost('/inbox/no-existe/responder').reply(404, { detail: 'HiloNoEncontrado' })
    await expect(responder('no-existe', { asunto: 'X', cuerpo: 'Y' })).rejects.toMatchObject({ status: 404 })
  })
})
