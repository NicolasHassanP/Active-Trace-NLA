/**
 * Mensajería TanStack Query hooks.
 * Queries para lectura, mutations para escritura con invalidación correcta de caché.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { abrirHilo, iniciarHilo, listarHilos, responder } from '../services/mensajeriaService'
import { buscarUsuariosInbox } from '../services/inboxUsuariosService'
import type { HiloCreate, RespuestaCreate } from '../types'

const KEYS = {
  hilos: ['mensajeria-hilos'] as const,
  hilo: (hiloId: string) => ['mensajeria-hilo', hiloId] as const,
}

/** Task 3.1 — GET /inbox: lista de hilos del usuario autenticado. Polls every 30s. */
export function useHilos({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: KEYS.hilos,
    queryFn: listarHilos,
    refetchInterval: enabled ? 30_000 : false,
    enabled,
  })
}

/** Total de mensajes no leídos en todos los hilos — para el badge de la campanita. */
export function useNoLeidosInbox(enabled = true): number {
  const { data: hilos = [] } = useQuery({
    queryKey: KEYS.hilos,
    queryFn: listarHilos,
    refetchInterval: enabled ? 30_000 : false,
    enabled,
  })
  return hilos.reduce((sum, h) => sum + (h.no_leidos ?? 0), 0)
}

/** Task 3.2 — GET /inbox/{hilo_id}: mensajes del hilo; enabled solo si hay hiloId. */
export function useHilo(hiloId: string | null) {
  const qc = useQueryClient()
  return useQuery({
    queryKey: KEYS.hilo(hiloId ?? ''),
    queryFn: async () => {
      const data = await abrirHilo(hiloId!)
      // Abrir marca leído server-side → refrescar lista para actualizar no_leidos
      void qc.invalidateQueries({ queryKey: KEYS.hilos })
      return data
    },
    enabled: !!hiloId,
  })
}

/** Task 3.3 — POST /inbox: inicia un hilo nuevo; invalida lista on success. */
export function useIniciarHilo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: HiloCreate) => iniciarHilo(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.hilos })
    },
  })
}

/** Task 3.4 — POST /inbox/{hilo_id}/responder; invalida hilo y lista on success. */
export function useResponder(hiloId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: RespuestaCreate) => responder(hiloId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.hilo(hiloId) })
      void qc.invalidateQueries({ queryKey: KEYS.hilos })
    },
  })
}

/**
 * Query hook for GET /api/v1/inbox/usuarios?q=...
 * Busca usuarios del tenant para el combobox de destinatario en mensajería.
 * Sólo activo cuando q tiene al menos 1 carácter (trim).
 * Usa placeholderData: keepPrevious para evitar parpadeo entre keystrokes.
 * Gateado por inbox:usar — mismo permiso que el inbox en general.
 */
export function useBuscarUsuariosInbox(q: string) {
  return useQuery({
    queryKey: ['inbox', 'usuarios', q] as const,
    queryFn: () => buscarUsuariosInbox(q),
    enabled: q.trim().length >= 1,
    placeholderData: (prev) => prev,
  })
}
