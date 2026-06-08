import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useTodasMaterias, useTodosCohortes } from '@/features/monitores/hooks/monitoresHooks'
import { useAtrasados } from '../hooks/atrasadosHooks'
import { useReporteMateria } from '../hooks/atrasadosHooks'
import AtrasadosTable from '../components/AtrasadosTable'
import AtrasadosFilters from '../components/AtrasadosFilters'
import ReporteMateriaHeader from '../components/ReporteMateriaHeader'
import { Button, PageHeader } from '@/shared/components/ui'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'
import type { Role } from '@/features/auth/types'

const GLOBAL_ROLES: Role[] = ['ADMIN']

export default function AtrasadosPage() {
  const { materiaId: paramMateriaId = '', cohorteId: paramCohorteId = '' } = useParams<{
    materiaId: string
    cohorteId: string
  }>()
  const navigate = useNavigate()
  const { roles } = useAuth()
  const isGlobalScope = roles.some((r) => GLOBAL_ROLES.includes(r))

  const hasUrlParams = Boolean(paramMateriaId && paramCohorteId)

  const [selectedKey, setSelectedKey] = useState('')
  const [selectedMateriaId, setSelectedMateriaId] = useState('')
  const [selectedCohorteId, setSelectedCohorteId] = useState('')
  const [selectedActividades, setSelectedActividades] = useState<string[]>([])
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set())

  const useSelector = !hasUrlParams

  const { data: asignaciones = [], isLoading: loadingAsignaciones } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => rows.filter((a) => a.materia_id && a.cohorte_id),
    enabled: useSelector && !isGlobalScope,
  })

  const { data: todasMaterias = [], isLoading: loadingMaterias } = useTodasMaterias(
    useSelector && isGlobalScope,
  )
  const { data: todosCohortes = [], isLoading: loadingCohortes } = useTodosCohortes(
    useSelector && isGlobalScope,
  )

  const loadingSelector = isGlobalScope ? loadingMaterias || loadingCohortes : loadingAsignaciones

  const selectedAsignacion = asignaciones.find(
    (a) => `${a.materia_id}__${a.cohorte_id}` === selectedKey,
  )

  const materiaId = hasUrlParams
    ? paramMateriaId
    : isGlobalScope
      ? selectedMateriaId
      : (selectedAsignacion?.materia_id ?? '')

  const cohorteId = hasUrlParams
    ? paramCohorteId
    : isGlobalScope
      ? selectedCohorteId
      : (selectedAsignacion?.cohorte_id ?? '')

  const atrasadosQuery = useAtrasados({
    materia_id: materiaId,
    cohorte_id: cohorteId,
  })

  const reporteQuery = useReporteMateria(materiaId, cohorteId)
  const alumnos = atrasadosQuery.data ?? []

  const alumnosFiltrados =
    selectedActividades.length > 0
      ? alumnos.filter((a) =>
          selectedActividades.some(
            (act) =>
              a.actividades_faltantes.includes(act) ||
              a.actividades_no_aprobadas.includes(act),
          ),
        )
      : alumnos

  function toggleSelect(email: string) {
    setSelectedEmails((prev) => {
      const next = new Set(prev)
      if (next.has(email)) next.delete(email)
      else next.add(email)
      return next
    })
  }

  function handleComunicar() {
    const emailsParam = Array.from(selectedEmails).join(',')
    navigate(
      `/comunicaciones?destinatarios=${encodeURIComponent(emailsParam)}&materia_id=${materiaId}&cohorte_id=${cohorteId}`,
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Alumnos atrasados" />

      {!hasUrlParams && (
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
                    setSelectedActividades([])
                    setSelectedEmails(new Set())
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
                      setSelectedActividades([])
                      setSelectedEmails(new Set())
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
                setSelectedActividades([])
                setSelectedEmails(new Set())
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
      )}

      {!materiaId && !loadingSelector && (
        <p className="text-sm text-gray-500 italic">
          Seleccioná una materia y cohorte para ver los atrasados.
        </p>
      )}

      {materiaId && cohorteId && (
        <>
          <ReporteMateriaHeader reporte={reporteQuery.data} isLoading={reporteQuery.isLoading} />

          {atrasadosQuery.isLoading && (
            <div className="text-sm text-gray-500">Cargando alumnos…</div>
          )}

          {atrasadosQuery.isError && (
            <div role="alert" className="text-sm text-red-600">
              Error al cargar la lista de atrasados.
            </div>
          )}

          {!atrasadosQuery.isLoading && !atrasadosQuery.isError && (
            <>
              <AtrasadosFilters
                alumnos={alumnos}
                selectedActividades={selectedActividades}
                onChangeActividades={setSelectedActividades}
              />

              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  {selectedEmails.size > 0
                    ? `${selectedEmails.size} alumno(s) seleccionado(s)`
                    : 'Seleccioná alumnos para comunicar'}
                </p>
                <Button
                  onClick={handleComunicar}
                  disabled={selectedEmails.size === 0}
                  data-testid="comunicar-btn"
                >
                  Comunicar a seleccionados
                </Button>
              </div>

              <AtrasadosTable
                alumnos={alumnosFiltrados}
                selectedEmails={selectedEmails}
                onToggleSelect={toggleSelect}
              />
            </>
          )}
        </>
      )}
    </div>
  )
}
