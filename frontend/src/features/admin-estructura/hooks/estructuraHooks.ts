/**
 * estructuraHooks — TanStack Query hooks for admin-estructura feature.
 *
 * Query keys are prefixed with ['admin-estructura', entity] so invalidation is
 * entity-scoped. Mutations invalidate ONLY their entity's root key.
 *
 * Permission: estructura:ver (queries), estructura:gestionar (mutations) → ADMIN.
 * Identity/tenant never in the body — resolved from the JWT via interceptor.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listarCarreras,
  crearCarrera,
  editarCarrera,
  darBajaCarrera,
  listarMaterias,
  crearMateria,
  editarMateria,
  darBajaMateria,
  listarCohortes,
  crearCohorte,
  editarCohorte,
  darBajaCohorte,
} from '../services/estructuraAdminService'
import type {
  CarreraCreate,
  CarreraUpdate,
  MateriaCreate,
  MateriaUpdate,
  CohorteCreate,
  CohorteUpdate,
} from '../types'

// Query key roots — used for invalidation
const CARRERAS_KEY = ['admin-estructura', 'carreras'] as const
const MATERIAS_KEY = ['admin-estructura', 'materias'] as const
const COHORTES_KEY = ['admin-estructura', 'cohortes'] as const

// ---------------------------------------------------------------------------
// Carreras — queries
// ---------------------------------------------------------------------------

/** Query hook for GET /api/v1/admin/carreras. */
export function useCarreras() {
  return useQuery({
    queryKey: CARRERAS_KEY,
    queryFn: () => listarCarreras(),
  })
}

// ---------------------------------------------------------------------------
// Carreras — mutations
// ---------------------------------------------------------------------------

/** Mutation hook for POST /api/v1/admin/carreras. Invalidates CARRERAS_KEY on success. */
export function useCrearCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CarreraCreate) => crearCarrera(body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: CARRERAS_KEY }) },
  })
}

/** Mutation hook for PATCH /api/v1/admin/carreras/{id}. */
export function useEditarCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CarreraUpdate }) => editarCarrera(id, body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: CARRERAS_KEY }) },
  })
}

/** Mutation hook for DELETE /api/v1/admin/carreras/{id}. */
export function useDarBajaCarrera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => darBajaCarrera(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: CARRERAS_KEY }) },
  })
}

// ---------------------------------------------------------------------------
// Materias — queries
// ---------------------------------------------------------------------------

/** Query hook for GET /api/v1/admin/materias. */
export function useMaterias() {
  return useQuery({
    queryKey: MATERIAS_KEY,
    queryFn: () => listarMaterias(),
  })
}

// ---------------------------------------------------------------------------
// Materias — mutations
// ---------------------------------------------------------------------------

/** Mutation hook for POST /api/v1/admin/materias. Invalidates MATERIAS_KEY on success. */
export function useCrearMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: MateriaCreate) => crearMateria(body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: MATERIAS_KEY }) },
  })
}

/** Mutation hook for PATCH /api/v1/admin/materias/{id}. */
export function useEditarMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: MateriaUpdate }) => editarMateria(id, body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: MATERIAS_KEY }) },
  })
}

/** Mutation hook for DELETE /api/v1/admin/materias/{id}. */
export function useDarBajaMateria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => darBajaMateria(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: MATERIAS_KEY }) },
  })
}

// ---------------------------------------------------------------------------
// Cohortes — queries
// ---------------------------------------------------------------------------

/**
 * Query hook for GET /api/v1/admin/cohortes[?carrera_id=].
 * Optional carrera_id filter — included in query key for cache separation.
 */
export function useCohortes(carrera_id?: string) {
  return useQuery({
    queryKey: [...COHORTES_KEY, carrera_id ?? null] as const,
    queryFn: () => listarCohortes(carrera_id),
  })
}

// ---------------------------------------------------------------------------
// Cohortes — mutations
// ---------------------------------------------------------------------------

/** Mutation hook for POST /api/v1/admin/cohortes. Invalidates COHORTES_KEY on success. */
export function useCrearCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CohorteCreate) => crearCohorte(body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: COHORTES_KEY }) },
  })
}

/** Mutation hook for PATCH /api/v1/admin/cohortes/{id}. */
export function useEditarCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CohorteUpdate }) => editarCohorte(id, body),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: COHORTES_KEY }) },
  })
}

/** Mutation hook for DELETE /api/v1/admin/cohortes/{id}. */
export function useDarBajaCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => darBajaCohorte(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: COHORTES_KEY }) },
  })
}
