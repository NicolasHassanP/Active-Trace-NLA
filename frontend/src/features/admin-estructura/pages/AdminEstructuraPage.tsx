/**
 * AdminEstructuraPage — /admin/estructura
 * ABM de carreras, materias y cohortes del tenant.
 * RBAC gate: ADMIN only (estructura:ver + estructura:gestionar). Fail-closed.
 * Tabs por entidad. < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/features/auth/hooks/useAuth'
import Forbidden403 from '@/shared/components/Forbidden403'
import { PageHeader } from '@/shared/components/ui'
import type { Role } from '@/features/auth/types'
import type {
  CarreraRead,
  MateriaRead,
  CohorteRead,
  CarreraCreate,
  CarreraUpdate,
  MateriaCreate,
  MateriaUpdate,
  CohorteCreate,
  CohorteUpdate,
} from '../types'
import type { DomainError } from '@/shared/services/domainError'
import {
  useCarreras,
  useMaterias,
  useCohortes,
  useCrearCarrera,
  useEditarCarrera,
  useDarBajaCarrera,
  useCrearMateria,
  useEditarMateria,
  useDarBajaMateria,
  useCrearCohorte,
  useEditarCohorte,
  useDarBajaCohorte,
} from '../hooks/estructuraHooks'
import CarrerasTable from '../components/CarrerasTable'
import MateriasTable from '../components/MateriasTable'
import CohortesTable from '../components/CohortesTable'
import CarreraForm from '../components/CarreraForm'
import MateriaForm from '../components/MateriaForm'
import CohorteForm from '../components/CohorteForm'

const ALLOWED_ROLES: Role[] = ['ADMIN']

type TabId = 'carreras' | 'materias' | 'cohortes'

function errorMsg(err: unknown): string {
  const e = err as Partial<DomainError>
  return e?.detail ?? 'Ocurrió un error inesperado'
}

export default function AdminEstructuraPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))
  if (!isAllowed) return <Forbidden403 />
  return <EstructuraContent />
}

function EstructuraContent() {
  const [tab, setTab] = useState<TabId>('carreras')

  return (
    <div className="space-y-6" data-testid="admin-estructura-page">
      <PageHeader
        title="Estructura académica"
        subtitle="Gestioná carreras, materias y cohortes del tenant."
      />

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6" aria-label="Secciones de estructura">
          {(['carreras', 'materias', 'cohortes'] as TabId[]).map((t) => (
            <button
              key={t}
              role="tab"
              type="button"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`pb-3 text-sm font-medium capitalize ${
                tab === t
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'carreras' && <CarrerasSection />}
      {tab === 'materias' && <MateriasSection />}
      {tab === 'cohortes' && <CohortesSection />}
    </div>
  )
}

// ── Carreras section ──────────────────────────────────────────────────────────

function CarrerasSection() {
  const [editing, setEditing] = useState<CarreraRead | null>(null)
  const [formError, setFormError] = useState<string | undefined>()
  const query = useCarreras()
  const crearMut = useCrearCarrera()
  const editarMut = useEditarCarrera()
  const bajaMut = useDarBajaCarrera()

  function handleSubmit(values: CarreraCreate | CarreraUpdate) {
    setFormError(undefined)
    if (editing) {
      editarMut.mutate({ id: editing.id, body: values as CarreraUpdate }, {
        onSuccess: () => { toast.success('Carrera actualizada'); setEditing(null) },
        onError: (err) => setFormError(errorMsg(err)),
      })
    } else {
      crearMut.mutate(values as CarreraCreate, {
        onSuccess: () => toast.success('Carrera creada'),
        onError: (err) => setFormError(errorMsg(err)),
      })
    }
  }

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">{editing ? 'Editar carrera' : 'Nueva carrera'}</h2>
        <CarreraForm
          initialValues={editing ?? undefined}
          onSubmit={handleSubmit}
          onCancel={() => { setEditing(null); setFormError(undefined) }}
          isSubmitting={crearMut.isPending || editarMut.isPending}
          errorMessage={formError}
        />
      </section>
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Carreras activas</h2>
        {query.isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
        {query.isError && <p role="alert" className="text-sm text-red-600">No se pudieron cargar las carreras.</p>}
        {!query.isLoading && !query.isError && (
          <CarrerasTable
            carreras={query.data ?? []}
            onEdit={setEditing}
            onDelete={(id) => bajaMut.mutate(id, {
              onSuccess: () => toast.success('Carrera dada de baja'),
              onError: (err) => toast.error(errorMsg(err)),
            })}
            isDeleting={bajaMut.isPending}
          />
        )}
      </section>
    </div>
  )
}

// ── Materias section ──────────────────────────────────────────────────────────

function MateriasSection() {
  const [editing, setEditing] = useState<MateriaRead | null>(null)
  const [formError, setFormError] = useState<string | undefined>()
  const query = useMaterias()
  const crearMut = useCrearMateria()
  const editarMut = useEditarMateria()
  const bajaMut = useDarBajaMateria()

  function handleSubmit(values: MateriaCreate | MateriaUpdate) {
    setFormError(undefined)
    if (editing) {
      editarMut.mutate({ id: editing.id, body: values as MateriaUpdate }, {
        onSuccess: () => { toast.success('Materia actualizada'); setEditing(null) },
        onError: (err) => setFormError(errorMsg(err)),
      })
    } else {
      crearMut.mutate(values as MateriaCreate, {
        onSuccess: () => toast.success('Materia creada'),
        onError: (err) => setFormError(errorMsg(err)),
      })
    }
  }

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">{editing ? 'Editar materia' : 'Nueva materia'}</h2>
        <MateriaForm
          initialValues={editing ?? undefined}
          onSubmit={handleSubmit}
          onCancel={() => { setEditing(null); setFormError(undefined) }}
          isSubmitting={crearMut.isPending || editarMut.isPending}
          errorMessage={formError}
        />
      </section>
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Materias activas</h2>
        {query.isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
        {query.isError && <p role="alert" className="text-sm text-red-600">No se pudieron cargar las materias.</p>}
        {!query.isLoading && !query.isError && (
          <MateriasTable
            materias={query.data ?? []}
            onEdit={setEditing}
            onDelete={(id) => bajaMut.mutate(id, {
              onSuccess: () => toast.success('Materia dada de baja'),
              onError: (err) => toast.error(errorMsg(err)),
            })}
            isDeleting={bajaMut.isPending}
          />
        )}
      </section>
    </div>
  )
}

// ── Cohortes section ──────────────────────────────────────────────────────────

function CohortesSection() {
  const [editing, setEditing] = useState<CohorteRead | null>(null)
  const [formError, setFormError] = useState<string | undefined>()
  const carrerasQuery = useCarreras()
  const query = useCohortes()
  const crearMut = useCrearCohorte()
  const editarMut = useEditarCohorte()
  const bajaMut = useDarBajaCohorte()

  function handleSubmit(values: CohorteCreate | CohorteUpdate) {
    setFormError(undefined)
    if (editing) {
      editarMut.mutate({ id: editing.id, body: values as CohorteUpdate }, {
        onSuccess: () => { toast.success('Cohorte actualizada'); setEditing(null) },
        onError: (err) => setFormError(errorMsg(err)),
      })
    } else {
      crearMut.mutate(values as CohorteCreate, {
        onSuccess: () => toast.success('Cohorte creada'),
        onError: (err) => setFormError(errorMsg(err)),
      })
    }
  }

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">{editing ? 'Editar cohorte' : 'Nueva cohorte'}</h2>
        <CohorteForm
          carreras={carrerasQuery.data ?? []}
          initialValues={editing ?? undefined}
          onSubmit={handleSubmit}
          onCancel={() => { setEditing(null); setFormError(undefined) }}
          isSubmitting={crearMut.isPending || editarMut.isPending}
          errorMessage={formError}
        />
      </section>
      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Cohortes activas</h2>
        {query.isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
        {query.isError && <p role="alert" className="text-sm text-red-600">No se pudieron cargar las cohortes.</p>}
        {!query.isLoading && !query.isError && (
          <CohortesTable
            cohortes={query.data ?? []}
            onEdit={setEditing}
            onDelete={(id) => bajaMut.mutate(id, {
              onSuccess: () => toast.success('Cohorte dada de baja'),
              onError: (err) => toast.error(errorMsg(err)),
            })}
            isDeleting={bajaMut.isPending}
          />
        )}
      </section>
    </div>
  )
}
