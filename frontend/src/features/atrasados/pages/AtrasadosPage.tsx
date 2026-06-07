/**
 * AtrasadosPage — reads materiaId/cohorteId from URL params when present,
 * otherwise shows a dropdown loaded from GET /perfil/mis-asignaciones.
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAtrasados } from '../hooks/atrasadosHooks'
import { useReporteMateria } from '../hooks/atrasadosHooks'
import AtrasadosTable from '../components/AtrasadosTable'
import AtrasadosFilters from '../components/AtrasadosFilters'
import ReporteMateriaHeader from '../components/ReporteMateriaHeader'
import { Button, PageHeader } from '@/shared/components/ui'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'

export default function AtrasadosPage() {
  const { materiaId: paramMateriaId = '', cohorteId: paramCohorteId = '' } = useParams<{
    materiaId: string
    cohorteId: string
  }>()
  const navigate = useNavigate()

  const hasUrlParams = Boolean(paramMateriaId && paramCohorteId)

  const [selectedKey, setSelectedKey] = useState('')
  const [selectedActividades, setSelectedActividades] = useState<string[]>([])
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set())

  const { data: asignaciones = [], isLoading: loadingAsignaciones } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => rows.filter((a) => a.materia_id && a.cohorte_id),
    enabled: !hasUrlParams,
  })

  const selectedAsignacion = asignaciones.find(
    (a) => `${a.materia_id}__${a.cohorte_id}` === selectedKey,
  )

  const materiaId = hasUrlParams ? paramMateriaId : (selectedAsignacion?.materia_id ?? '')
  const cohorteId = hasUrlParams ? paramCohorteId : (selectedAsignacion?.cohorte_id ?? '')

  const atrasadosQuery = useAtrasados({
    materia_id: materiaId,
    cohorte_id: cohorteId,
    actividades: selectedActividades.length > 0 ? selectedActividades : undefined,
  })

  const reporteQuery = useReporteMateria(materiaId, cohorteId)
  const alumnos = atrasadosQuery.data ?? []

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

          {loadingAsignaciones ? (
            <p className="text-sm text-gray-500">Cargando materias…</p>
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

      {!materiaId && !loadingAsignaciones && (
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
                alumnos={alumnos}
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
