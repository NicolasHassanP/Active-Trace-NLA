/**
 * AvisosPage — main page for the Avisos feature.
 * RBAC: COORDINADOR/ADMIN see management panel (publish, edit, delete).
 *       Any authenticated user sees the bandeja (feed + ack).
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 2.7, 2.8. < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useAvisosGestion, useAvisosFeed, useAvisosPendientes, useEliminarAviso } from '../hooks/avisosHooks'
import AvisoForm from '../components/AvisoForm'
import AvisosTable from '../components/AvisosTable'
import BandejaAvisos from '../components/BandejaAvisos'
import type { AvisoRead } from '../types'
import type { Role } from '@/features/auth/types'
import { toast } from 'sonner'
import { Button, PageHeader } from '@/shared/components/ui'

const MANAGEMENT_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function AvisosPage() {
  const { roles } = useAuth()
  const isManager = roles.some((r) => MANAGEMENT_ROLES.includes(r))

  const feedQuery = useAvisosFeed()
  const pendientesQuery = useAvisosPendientes()
  const gestionQuery = useAvisosGestion()
  const eliminarMutation = useEliminarAviso()

  const [editingAviso, setEditingAviso] = useState<AvisoRead | null>(null)
  const [showForm, setShowForm] = useState(false)

  function handleDelete(avisoId: string) {
    if (!confirm('¿Eliminar este aviso?')) return
    eliminarMutation.mutate(avisoId, {
      onSuccess: () => toast.success('Aviso eliminado'),
      onError: (err) => toast.error((err as { detail?: string }).detail ?? 'Error'),
    })
  }

  function handleEdit(aviso: AvisoRead) {
    setEditingAviso(aviso)
    setShowForm(true)
  }

  function closeForm() {
    setEditingAviso(null)
    setShowForm(false)
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Avisos" />

      {/* Management panel — COORDINADOR / ADMIN only */}
      {isManager && (
        <section data-testid="avisos-gestion" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-700">Gestión de avisos</h2>
            <Button
              variant="primary"
              size="sm"
              onClick={() => { setEditingAviso(null); setShowForm(true) }}
            >
              Nuevo aviso
            </Button>
          </div>

          {showForm && (
            <div className="rounded-lg border border-gray-200 p-4">
              <AvisoForm editing={editingAviso ?? undefined} onClose={closeForm} />
            </div>
          )}

          {gestionQuery.isLoading && <p className="text-sm text-gray-500">Cargando avisos…</p>}
          {gestionQuery.isError && (
            <div role="alert" className="text-sm text-red-600">Error al cargar la lista de avisos.</div>
          )}
          {!gestionQuery.isLoading && !gestionQuery.isError && (
            <AvisosTable
              avisos={gestionQuery.data ?? []}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          )}
        </section>
      )}

      {/* Bandeja — all authenticated users */}
      <section data-testid="avisos-bandeja">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Mis avisos</h2>
        <BandejaAvisos
          avisos={feedQuery.data ?? []}
          pendientes={pendientesQuery.data ?? []}
          isLoading={feedQuery.isLoading}
        />
      </section>
    </div>
  )
}
