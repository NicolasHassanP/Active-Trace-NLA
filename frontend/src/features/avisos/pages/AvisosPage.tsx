/**
 * AvisosPage — main page for the Avisos feature.
 * RBAC: COORDINADOR/ADMIN see management panel (publish, edit, delete).
 *       Any authenticated user sees the bandeja (feed + ack).
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 2.7, 2.8. < 200 LOC.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useAvisosGestion, useAvisosFeed, useAvisosPendientes, useEliminarAviso } from '../hooks/avisosHooks'
import { useHilos } from '@/features/mensajeria/hooks/mensajeriaHooks'
import AvisoForm from '../components/AvisoForm'
import AvisosTable from '../components/AvisosTable'
import BandejaAvisos from '../components/BandejaAvisos'
import type { AvisoRead } from '../types'
import type { Role } from '@/features/auth/types'
import { toast } from 'sonner'
import { Button, PageHeader } from '@/shared/components/ui'

const MANAGEMENT_ROLES: Role[] = ['COORDINADOR', 'ADMIN']
const MESSAGING_ROLES: Role[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']

export default function AvisosPage() {
  const navigate = useNavigate()
  const { roles } = useAuth()
  const isManager = roles.some((r) => MANAGEMENT_ROLES.includes(r))
  const hasMessaging = roles.some((r) => MESSAGING_ROLES.includes(r))

  const feedQuery = useAvisosFeed()
  const pendientesQuery = useAvisosPendientes()
  const gestionQuery = useAvisosGestion(isManager)
  const eliminarMutation = useEliminarAviso()

  const { data: hilos = [] } = useHilos({ enabled: hasMessaging })
  const hilosNoLeidos = hilos.filter((h) => h.no_leidos > 0)

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

      {/* Mensajes sin leer — solo roles con acceso a mensajería */}
      {hasMessaging && hilosNoLeidos.length > 0 && (
        <section data-testid="mensajes-notificaciones" className="space-y-2">
          <h2 className="text-lg font-semibold text-gray-700">Mensajes sin leer</h2>
          <div className="space-y-2">
            {hilosNoLeidos.map((hilo) => (
              <button
                key={hilo.id}
                type="button"
                onClick={() => navigate(`/mensajes?hilo=${hilo.id}`)}
                className="w-full text-left flex items-center gap-3 rounded-lg border border-line bg-white px-4 py-3 hover:bg-indBg hover:border-ind transition-colors"
              >
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-indBg flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-ind" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-ink truncate">
                    {hilo.otro_participante_nombre ?? '(sin nombre)'}
                  </p>
                  {hilo.asunto && (
                    <p className="text-xs text-mut truncate">{hilo.asunto}</p>
                  )}
                </div>
                <span className="flex-shrink-0 min-w-[20px] h-5 rounded-full bg-warn text-white text-[11px] font-bold flex items-center justify-center px-1">
                  {hilo.no_leidos}
                </span>
              </button>
            ))}
          </div>
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
