/**
 * ResultadosPanel — shows academic results for a single convocatoria.
 * Fetches data via useResultados (TanStack Query) and delegates rendering
 * to ResultadosTable. Provides a "Volver" button to dismiss the panel.
 * Task 6.11 — batch 4 routing followup. < 200 LOC. Tailwind only.
 */
import { useResultados } from '../hooks/coloquiosHooks'
import ResultadosTable from './ResultadosTable'
import { Button } from '@/shared/components/ui'

interface Props {
  evaluacionId: string
  onVolver: () => void
}

export default function ResultadosPanel({ evaluacionId, onVolver }: Props) {
  const { data, isLoading, isError } = useResultados(evaluacionId)

  return (
    <section data-testid="resultados-panel" className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onVolver}>
          ← Volver
        </Button>
        <h2 className="text-lg font-semibold text-gray-800">
          Resultados de convocatoria
        </h2>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500">Cargando resultados…</p>
      )}

      {isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          Error al cargar los resultados. Intentá nuevamente.
        </div>
      )}

      {!isLoading && !isError && (
        <ResultadosTable resultados={data ?? []} />
      )}
    </section>
  )
}
