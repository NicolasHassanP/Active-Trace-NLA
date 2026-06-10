/**
 * TareasPage — main page for the Tareas feature.
 * RBAC:
 *   - Mis tareas: TUTOR, PROFESOR, COORDINADOR, ADMIN (any authenticated role listed in the route).
 *   - Admin panel (filtros + alta + cambio de estado): COORDINADOR, ADMIN only.
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 3.8. < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useMisTareas, useTareasAdmin } from '../hooks/tareasHooks'
import MisTareasList from '../components/MisTareasList'
import TareasAdminTable from '../components/TareasAdminTable'
import TareasFilters from '../components/TareasFilters'
import TareaForm from '../components/TareaForm'
import type { TareasAdminParams, TareaEstado } from '../types'
import type { Role } from '@/features/auth/types'
import { toast } from 'sonner'
import { useCambiarEstado } from '../hooks/tareasHooks'
import { Button, PageHeader } from '@/shared/components/ui'

const ADMIN_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function TareasPage() {
  const { roles } = useAuth()
  const isAdmin = roles.some((r) => ADMIN_ROLES.includes(r))

  const misTareasQuery = useMisTareas()
  const [adminParams, setAdminParams] = useState<TareasAdminParams>({})
  const tareasAdminQuery = useTareasAdmin(adminParams)
  const cambiarEstadoMutation = useCambiarEstado()

  const [showForm, setShowForm] = useState(false)
  const [selectedTareaId, setSelectedTareaId] = useState<string | null>(null)

  function handleCambiarEstado(tareaId: string, estado: TareaEstado) {
    cambiarEstadoMutation.mutate(
      { tareaId, body: { estado } },
      {
        onSuccess: () => toast.success(`Estado cambiado a ${estado}`),
        onError: (err) => toast.error((err as { detail?: string }).detail ?? 'Error al cambiar estado'),
      },
    )
  }

  function handleDelegar(tareaId: string) {
    // Placeholder — opens a dialog in a full implementation
    toast.info(`Delegar tarea ${tareaId} — funcionalidad de delegación`)
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Tareas" />

      {/* Admin panel — COORDINADOR / ADMIN only */}
      {isAdmin && (
        <section data-testid="tareas-admin" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-700">Panel de administración</h2>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowForm((v) => !v)}
            >
              Nueva tarea
            </Button>
          </div>

          {showForm && (
            <div className="rounded-lg border border-gray-200 p-4">
              <TareaForm onClose={() => setShowForm(false)} />
            </div>
          )}

          <TareasFilters onFilter={setAdminParams} />

          {tareasAdminQuery.isLoading && (
            <p className="text-sm text-gray-500">Cargando tareas…</p>
          )}
          {tareasAdminQuery.isError && (
            <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
              Error al cargar las tareas.
            </div>
          )}
          {!tareasAdminQuery.isLoading && !tareasAdminQuery.isError && (
            <TareasAdminTable
              tareas={tareasAdminQuery.data ?? []}
              onCambiarEstado={handleCambiarEstado}
              onDelegar={handleDelegar}
              selectedTareaId={selectedTareaId}
              onSelect={setSelectedTareaId}
            />
          )}
        </section>
      )}

      {/* Mis tareas — all authorized roles */}
      <section data-testid="tareas-mias">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Mis tareas</h2>

        {misTareasQuery.isLoading && (
          <p className="text-sm text-gray-500">Cargando mis tareas…</p>
        )}

        {misTareasQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            Error al cargar las tareas asignadas.
          </div>
        )}

        {!misTareasQuery.isLoading && !misTareasQuery.isError && (
          <MisTareasList
            tareas={misTareasQuery.data ?? []}
            selectedTareaId={selectedTareaId}
            onSelect={setSelectedTareaId}
          />
        )}
      </section>
    </div>
  )
}
