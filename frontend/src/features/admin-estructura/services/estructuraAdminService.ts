/**
 * estructuraAdminService — wraps the Estructura ABM API endpoints.
 * All endpoints require ADMIN role.
 * GET (lectura) → estructura:ver; POST/PATCH/DELETE → estructura:gestionar.
 * Identity/tenant never in the request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 *
 * Endpoints:
 *   GET    /api/v1/admin/carreras                  — list carreras (estructura:ver)
 *   POST   /api/v1/admin/carreras                  — create (estructura:gestionar)
 *   PATCH  /api/v1/admin/carreras/{id}             — partial update
 *   DELETE /api/v1/admin/carreras/{id}             — soft delete (204)
 *
 *   GET    /api/v1/admin/materias                  — list materias
 *   POST   /api/v1/admin/materias                  — create
 *   PATCH  /api/v1/admin/materias/{id}             — partial update
 *   DELETE /api/v1/admin/materias/{id}             — soft delete (204)
 *
 *   GET    /api/v1/admin/cohortes[?carrera_id=]    — list cohortes
 *   POST   /api/v1/admin/cohortes                  — create
 *   PATCH  /api/v1/admin/cohortes/{id}             — partial update
 *   DELETE /api/v1/admin/cohortes/{id}             — soft delete (204)
 *
 * Domain exceptions mapped by backend:
 *   ConflictoUnicidad         → 409
 *   CarreraInactiva           → 409
 *   CarreraConCohorteAbiertas → 409
 *   *NoEncontrada             → 404
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  CarreraRead,
  CarreraCreate,
  CarreraUpdate,
  MateriaRead,
  MateriaCreate,
  MateriaUpdate,
  CohorteRead,
  CohorteCreate,
  CohorteUpdate,
} from '../types'

// ---------------------------------------------------------------------------
// Carreras
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/admin/carreras
 * Returns carreras for the current tenant (tenant-scoped on the backend).
 */
export async function listarCarreras(): Promise<CarreraRead[]> {
  try {
    const response = await apiClient.get<CarreraRead[]>('/admin/carreras')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/admin/carreras
 * Creates a new carrera. Returns the created CarreraRead on 201.
 * tenant_id resolved from the JWT — never in the body.
 */
export async function crearCarrera(body: CarreraCreate): Promise<CarreraRead> {
  try {
    const response = await apiClient.post<CarreraRead>('/admin/carreras', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/admin/carreras/{id}
 * Partial update of a carrera. Returns the updated CarreraRead on 200.
 */
export async function editarCarrera(id: string, body: CarreraUpdate): Promise<CarreraRead> {
  try {
    const response = await apiClient.patch<CarreraRead>(`/admin/carreras/${id}`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /api/v1/admin/carreras/{id}
 * Soft delete (baja lógica). Returns undefined on 204.
 */
export async function darBajaCarrera(id: string): Promise<void> {
  try {
    await apiClient.delete(`/admin/carreras/${id}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Materias
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/admin/materias
 */
export async function listarMaterias(): Promise<MateriaRead[]> {
  try {
    const response = await apiClient.get<MateriaRead[]>('/admin/materias')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/admin/materias
 */
export async function crearMateria(body: MateriaCreate): Promise<MateriaRead> {
  try {
    const response = await apiClient.post<MateriaRead>('/admin/materias', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/admin/materias/{id}
 */
export async function editarMateria(id: string, body: MateriaUpdate): Promise<MateriaRead> {
  try {
    const response = await apiClient.patch<MateriaRead>(`/admin/materias/${id}`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /api/v1/admin/materias/{id}
 */
export async function darBajaMateria(id: string): Promise<void> {
  try {
    await apiClient.delete(`/admin/materias/${id}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Cohortes
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/admin/cohortes[?carrera_id=]
 * Optional carrera_id filter — omitted when not provided.
 */
export async function listarCohortes(carrera_id?: string): Promise<CohorteRead[]> {
  try {
    const params = carrera_id ? { carrera_id } : undefined
    const response = await apiClient.get<CohorteRead[]>('/admin/cohortes', { params })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/admin/cohortes
 * carrera_id required; vig_hasta nullable = cohorte abierta.
 */
export async function crearCohorte(body: CohorteCreate): Promise<CohorteRead> {
  try {
    // Normalise: if vig_hasta is undefined, send null (open cohorte)
    const payload: CohorteCreate = {
      ...body,
      vig_hasta: body.vig_hasta ?? null,
    }
    const response = await apiClient.post<CohorteRead>('/admin/cohortes', payload)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/admin/cohortes/{id}
 */
export async function editarCohorte(id: string, body: CohorteUpdate): Promise<CohorteRead> {
  try {
    const response = await apiClient.patch<CohorteRead>(`/admin/cohortes/${id}`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /api/v1/admin/cohortes/{id}
 */
export async function darBajaCohorte(id: string): Promise<void> {
  try {
    await apiClient.delete(`/admin/cohortes/${id}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}
