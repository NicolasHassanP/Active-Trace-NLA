import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useTodasMaterias, useTodosCohortes } from '@/features/monitores/hooks/monitoresHooks'
import { useSeguimiento } from '../hooks/seguimientoHooks'
import SeguimientoFiltros from '../components/SeguimientoFiltros'
import SeguimientoTable from '../components/SeguimientoTable'
import type { SeguimientoParams } from '../types'
import { PageHeader, Card, CardContent, StatusBadge } from '@/shared/components/ui'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'
import type { Role } from '@/features/auth/types'

const GLOBAL_ROLES: Role[] = ['ADMIN']

export default function SeguimientoPage() {
  const { roles } = useAuth()
  const isGlobalScope = roles.some((r) => GLOBAL_ROLES.includes(r))

  const [selectedKey, setSelectedKey] = useState('')
  const [selectedMateriaId, setSelectedMateriaId] = useState('')
  const [selectedCohorteId, setSelectedCohorteId] = useState('')
  const [filterParams, setFilterParams] = useState<Omit<SeguimientoParams, 'materia_id' | 'cohorte_id'>>({})

  const { data: asignaciones = [], isLoading: loadingAsignaciones } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => rows.filter((a) => a.materia_id && a.cohorte_id),
    enabled: !isGlobalScope,
  })

  const { data: todasMaterias = [], isLoading: loadingMaterias } = useTodasMaterias(isGlobalScope)
  const { data: todosCohortes = [], isLoading: loadingCohortes } = useTodosCohortes(isGlobalScope)

  const loadingSelector = isGlobalScope ? loadingMaterias || loadingCohortes : loadingAsignaciones

  const selectedAsignacion = asignaciones.find(
    (a) => `${a.materia_id}__${a.cohorte_id}` === selectedKey,
  )

  const materiaId = isGlobalScope ? selectedMateriaId : (selectedAsignacion?.materia_id ?? '')
  const cohorteId = isGlobalScope ? selectedCohorteId : (selectedAsignacion?.cohorte_id ?? '')

  const params: SeguimientoParams = {
    materia_id: materiaId || null,
    cohorte_id: cohorteId || null,
    ...filterParams,
  }

  const query = useSeguimiento(params)

  const filas = query.data ?? []
  const totalAlumnos = filas.length
  const totalAtrasados = filas.filter((f) => f.estado === 'atrasado').length

  function handleFilter(newParams: SeguimientoParams) {
    const { materia_id: _m, cohorte_id: _c, ...rest } = newParams
    setFilterParams(rest)
  }

  function handleClear() {
    setFilterParams({})
  }

  return (
    <div data-testid="seguimiento-panel" className="space-y-6">
      <PageHeader title="Seguimiento de alumnos" />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>

        {loadingSelector ? (
          <p className="text-sm text-gray-500">Cargando materias…</p>
        ) : isGlobalScope ? (
          <div className="space-y-3">
            {todasMaterias.length === 0 ? (
              <p className="text-sm text-red-600">No hay materias registradas en el tenant.</p>
            ) : (
              <select
                value={selectedMateriaId}
                onChange={(e) => {
                  setSelectedMateriaId(e.target.value)
                  setSelectedCohorteId('')
                  setFilterParams({})
                }}
                className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
                data-testid="selector-materia"
              >
                <option value="">— Seleccioná una materia —</option>
                {todasMaterias.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </select>
            )}

            {selectedMateriaId && (
              todosCohortes.length === 0 ? (
                <p className="text-sm text-red-600">No hay cohortes registradas en el tenant.</p>
              ) : (
                <select
                  value={selectedCohorteId}
                  onChange={(e) => {
                    setSelectedCohorteId(e.target.value)
                    setFilterParams({})
                  }}
                  className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
                  data-testid="selector-cohorte"
                >
                  <option value="">— Seleccioná una cohorte —</option>
                  {todosCohortes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre} ({c.anio})
                    </option>
                  ))}
                </select>
              )
            )}
          </div>
        ) : asignaciones.length === 0 ? (
          <p className="text-sm text-red-600">
            No tenés materias asignadas con cohorte. Contactá al coordinador.
          </p>
        ) : (
          <select
            value={selectedKey}
            onChange={(e) => {
              setSelectedKey(e.target.value)
              setFilterParams({})
            }}
            className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
            data-testid="selector-asignacion"
          >
            <option value="">— Seleccioná una materia —</option>
            {asignaciones.map((a) => {
              const key = `${a.materia_id}__${a.cohorte_id}`
              return (
                <option key={key} value={key}>
                  {a.materia_nombre ?? a.materia_id} · {a.cohorte_nombre ?? a.cohorte_id}
                </option>
              )
            })}
          </select>
        )}
      </section>

      {!materiaId && !loadingSelector && (
        <p className="text-sm text-gray-500 italic">
          Seleccioná una materia y cohorte para ver el seguimiento.
        </p>
      )}

      {materiaId && cohorteId && (
        <>
          {!query.isLoading && !query.isError && (
            <Card>
              <CardContent>
                <div
                  data-testid="seguimiento-counters"
                  className="flex items-center gap-4 text-sm text-gray-600"
                >
                  <span>
                    <span className="font-semibold text-gray-900">{totalAlumnos}</span>{' '}
                    {totalAlumnos === 1 ? 'alumno' : 'alumnos'}
                  </span>
                  {totalAtrasados > 0 && (
                    <StatusBadge
                      status="atrasado"
                      label={`${totalAtrasados} atrasado${totalAtrasados !== 1 ? 's' : ''}`}
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          <SeguimientoFiltros onFilter={handleFilter} onClear={handleClear} />

          {query.isLoading && (
            <p className="text-sm text-gray-500">Cargando seguimiento…</p>
          )}

          {query.isError && (
            <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
              Error al cargar el seguimiento. Intentá de nuevo.
            </div>
          )}

          {!query.isLoading && !query.isError && (
            <SeguimientoTable filas={filas} />
          )}
        </>
      )}
    </div>
  )
}
