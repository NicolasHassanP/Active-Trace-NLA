/**
 * AsignacionesPage — "Gestión global de asignaciones" (M3 / F4.3).
 *
 * Shows the create form (AsignacionForm) and the filtered list (AsignacionesTable).
 * Supports inline edit mode: clicking "Editar" on a row switches the form to PATCH mode.
 *
 * Identity/tenant never sent from the client — resolved from the JWT on the backend.
 * Access: COORDINADOR / ADMIN (equipos:asignar). < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { PageHeader } from '@/shared/components/ui'
import type { DomainError } from '@/shared/services/domainError'
import {
  useAsignaciones,
  useCrearAsignacion,
  useEditarAsignacion,
  useDarBajaAsignacion,
} from '../hooks/asignacionHooks'
import AsignacionForm from '../components/AsignacionForm'
import AsignacionesTable from '../components/AsignacionesTable'
import type {
  AsignacionCreate,
  AsignacionRead,
  AsignacionUpdate,
} from '../types'
import type { AsignacionFormValues } from '../components/AsignacionForm'

function errorMessage(err: unknown): string {
  const e = err as Partial<DomainError>
  return e?.detail ?? 'Ocurrió un error inesperado'
}

function asignacionToFormValues(a: AsignacionRead): AsignacionFormValues {
  return {
    usuario_id: a.usuario_id,
    rol: a.rol,
    desde: a.desde,
    hasta: a.hasta,
    materia_id: a.materia_id,
    carrera_id: a.carrera_id,
    cohorte_id: a.cohorte_id,
    responsable_id: a.responsable_id,
  }
}

export default function AsignacionesPage() {
  const [editingRow, setEditingRow] = useState<AsignacionRead | null>(null)

  // Always fetch the full list — filtering is done client-side in AsignacionesTable.
  const asignacionesQuery = useAsignaciones({})
  const crearMutation = useCrearAsignacion()
  const editarMutation = useEditarAsignacion()
  const bajaMutation = useDarBajaAsignacion()

  const isSubmitting = crearMutation.isPending || editarMutation.isPending

  function handleSubmit(values: AsignacionCreate | AsignacionUpdate) {
    if (editingRow) {
      editarMutation.mutate(
        { id: editingRow.id, body: values as AsignacionUpdate },
        {
          onSuccess: () => {
            toast.success('Asignación actualizada')
            setEditingRow(null)
          },
          onError: (err) => toast.error(errorMessage(err)),
        },
      )
    } else {
      crearMutation.mutate(values as AsignacionCreate, {
        onSuccess: () => toast.success('Asignación creada'),
        onError: (err) => toast.error(errorMessage(err)),
      })
    }
  }

  function handleEdit(asignacion: AsignacionRead) {
    setEditingRow(asignacion)
  }

  function handleCancelEdit() {
    setEditingRow(null)
  }

  function handleDelete(id: string) {
    bajaMutation.mutate(id, {
      onSuccess: () => toast.success('Asignación dada de baja'),
      onError: (err) => toast.error(errorMessage(err)),
    })
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Gestión de asignaciones"
        subtitle="Creá, editá y gestioná las asignaciones del equipo docente."
      />

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">
          {editingRow ? 'Editar asignación' : 'Nueva asignación'}
        </h2>
        <AsignacionForm
          initialValues={editingRow ? asignacionToFormValues(editingRow) : undefined}
          onSubmit={handleSubmit}
          onCancel={handleCancelEdit}
          isSubmitting={isSubmitting}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Asignaciones activas</h2>

        {asignacionesQuery.isLoading && (
          <p className="text-sm text-gray-500">Cargando asignaciones…</p>
        )}

        {asignacionesQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            No se pudieron cargar las asignaciones. Intentá nuevamente.
          </div>
        )}

        {!asignacionesQuery.isLoading && !asignacionesQuery.isError && (
          <AsignacionesTable
            asignaciones={asignacionesQuery.data ?? []}
            onEdit={handleEdit}
            onDelete={handleDelete}
            isDeleting={bajaMutation.isPending}
          />
        )}
      </section>
    </div>
  )
}
