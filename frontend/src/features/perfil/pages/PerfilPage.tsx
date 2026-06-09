/**
 * PerfilPage — "Editar mi perfil".
 * Loads the own profile (identity from JWT), renders PerfilForm, handles submit.
 * Accessible to ANY authenticated user (perfil:editar is universal). < 200 LOC.
 */
import { toast } from 'sonner'
import { PageHeader } from '@/shared/components/ui'
import type { DomainError } from '@/shared/services/domainError'
import { usePerfil, useUpdatePerfil } from '../hooks/perfilHooks'
import PerfilForm from '../components/PerfilForm'
import type { PerfilUpdate } from '../types'

function errorMessage(err: unknown): string {
  const e = err as Partial<DomainError>
  if (e?.status === 409) return 'email ya usado en el tenant'
  return e?.detail ?? 'No se pudo guardar el perfil'
}

export default function PerfilPage() {
  const perfilQuery = usePerfil()
  const updateMutation = useUpdatePerfil()

  function handleSubmit(body: PerfilUpdate) {
    updateMutation.mutate(body, {
      onSuccess: () => toast.success('Perfil actualizado'),
      onError: (err) => toast.error(errorMessage(err)),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Mi perfil" subtitle="Editá tus datos personales y de facturación." />

      {perfilQuery.isLoading && (
        <p className="text-sm text-gray-500">Cargando perfil…</p>
      )}

      {perfilQuery.isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          No se pudo cargar el perfil. Intentá nuevamente.
        </div>
      )}

      {perfilQuery.data && (
        <PerfilForm
          perfil={perfilQuery.data}
          onSubmit={handleSubmit}
          isSubmitting={updateMutation.isPending}
        />
      )}
    </div>
  )
}
