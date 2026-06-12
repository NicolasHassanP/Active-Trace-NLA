/**
 * usuarioAdminHooks — TanStack Query hooks for admin-usuarios feature.
 *
 * Query keys are prefixed with ['admin-usuarios'] so invalidation is
 * scoped to this feature. Mutations invalidate USUARIOS_KEY on success.
 *
 * Permission: usuarios:gestionar (all) → ADMIN.
 * Identity/tenant never in the body — resolved from the JWT via interceptor.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listarUsuarios,
  crearUsuario,
  editarUsuario,
  darBajaUsuario,
} from '../services/usuarioAdminService'
import type { UsuarioCreate, UsuarioUpdate } from '../types'

// Query key root — used for invalidation
const USUARIOS_KEY = ['admin-usuarios', 'usuarios'] as const

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

/** Query hook for GET /api/v1/admin/usuarios. */
export function useUsuarios() {
  return useQuery({
    queryKey: USUARIOS_KEY,
    queryFn: () => listarUsuarios(),
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/** Mutation hook for POST /api/v1/admin/usuarios. Invalidates USUARIOS_KEY on success. */
export function useCrearUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: UsuarioCreate) => crearUsuario(body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: USUARIOS_KEY }) },
  })
}

/** Mutation hook for PATCH /api/v1/admin/usuarios/{id}. Invalidates USUARIOS_KEY on success. */
export function useEditarUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UsuarioUpdate }) => editarUsuario(id, body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: USUARIOS_KEY }) },
  })
}

/** Mutation hook for DELETE /api/v1/admin/usuarios/{id}. Invalidates USUARIOS_KEY on success. */
export function useDarBajaUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => darBajaUsuario(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: USUARIOS_KEY }) },
  })
}
