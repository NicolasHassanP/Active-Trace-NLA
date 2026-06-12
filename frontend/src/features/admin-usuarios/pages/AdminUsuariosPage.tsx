/**
 * AdminUsuariosPage — /admin/usuarios
 * ABM de usuarios del tenant (non-PII only, contrato OQ-3).
 * RBAC gate: ADMIN only (usuarios:gestionar). Fail-closed.
 * < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/features/auth/hooks/useAuth'
import Forbidden403 from '@/shared/components/Forbidden403'
import { PageHeader } from '@/shared/components/ui'
import type { Role } from '@/features/auth/types'
import type { UsuarioRead, UsuarioCreate, UsuarioUpdate } from '../types'
import type { DomainError } from '@/shared/services/domainError'
import {
  useUsuarios,
  useCrearUsuario,
  useEditarUsuario,
  useDarBajaUsuario,
} from '../hooks/usuarioAdminHooks'
import UsuariosTable from '../components/UsuariosTable'
import UsuarioForm from '../components/UsuarioForm'

const ALLOWED_ROLES: Role[] = ['ADMIN']

function errorMsg(err: unknown): string {
  const e = err as Partial<DomainError>
  return e?.detail ?? 'Ocurrió un error inesperado'
}

export default function AdminUsuariosPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))
  if (!isAllowed) return <Forbidden403 />
  return <UsuariosContent />
}

function UsuariosContent() {
  const [editing, setEditing] = useState<UsuarioRead | null>(null)
  const [formError, setFormError] = useState<string | undefined>()

  const query = useUsuarios()
  const crearMut = useCrearUsuario()
  const editarMut = useEditarUsuario()
  const bajaMut = useDarBajaUsuario()

  function handleSubmit(values: UsuarioCreate | UsuarioUpdate) {
    setFormError(undefined)
    if (editing) {
      editarMut.mutate(
        { id: editing.id, body: values as UsuarioUpdate },
        {
          onSuccess: () => {
            toast.success('Usuario actualizado')
            setEditing(null)
          },
          onError: (err) => setFormError(errorMsg(err)),
        }
      )
    } else {
      crearMut.mutate(values as UsuarioCreate, {
        onSuccess: () => toast.success('Usuario creado'),
        onError: (err) => setFormError(errorMsg(err)),
      })
    }
  }

  return (
    <div className="space-y-6" data-testid="admin-usuarios-page">
      <PageHeader
        title="Usuarios"
        subtitle="Gestioná los usuarios del tenant. Solo campos no-PII (OQ-3)."
      />

      {/* Form section */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">
          {editing ? 'Editar usuario' : 'Nuevo usuario'}
        </h2>
        <UsuarioForm
          initialValues={editing ?? undefined}
          onSubmit={handleSubmit}
          onCancel={() => { setEditing(null); setFormError(undefined) }}
          isSubmitting={crearMut.isPending || editarMut.isPending}
          errorMessage={formError}
        />
      </section>

      {/* Table section */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Usuarios del tenant</h2>
        {query.isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
        {query.isError && (
          <p role="alert" className="text-sm text-red-600">
            No se pudieron cargar los usuarios.
          </p>
        )}
        {!query.isLoading && !query.isError && (
          <UsuariosTable
            usuarios={query.data ?? []}
            onEdit={setEditing}
            onDelete={(id) =>
              bajaMut.mutate(id, {
                onSuccess: () => toast.success('Usuario dado de baja'),
                onError: (err) => toast.error(errorMsg(err)),
              })
            }
            isDeleting={bajaMut.isPending}
          />
        )}
      </section>
    </div>
  )
}
