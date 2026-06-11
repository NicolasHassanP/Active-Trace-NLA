/**
 * MiCursadaPage — página exclusiva del rol ALUMNO.
 * Task 6.4: avance global + materias cursadas + coloquios reservados.
 *
 * Sin max-w-* ni mx-auto en el root wrapper (ocupa todo el espacio del shell).
 * Identidad siempre del JWT (sin props de user_id).
 */
import { PageHeader } from '@/shared/components/ui/PageHeader'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { useEstadoAcademico } from '../hooks/miCursadaHooks'
import { AvanceKpis } from '../components/AvanceKpis'
import { MateriasCursadasTable } from '../components/MateriasCursadasTable'
import { ColoquiosReservadosPanel } from '../components/ColoquiosReservadosPanel'

export default function MiCursadaPage() {
  const { data: estado, isLoading, isError } = useEstadoAcademico()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mi cursada"
        subtitle="Tu avance académico, actividades y coloquios reservados."
      />

      {isLoading && (
        <p className="text-[13px] text-mut py-4">Cargando tu estado académico…</p>
      )}

      {isError && (
        <EmptyState
          title="No se pudo cargar el estado académico"
          description="Intentá recargar la página. Si el problema persiste, contactá al soporte."
        />
      )}

      {estado && (
        <>
          <AvanceKpis estado={estado} />

          <section>
            <h2 className="text-[15px] font-bold text-ink mb-3">Materias cursadas</h2>
            {estado.materias.length === 0 ? (
              <EmptyState
                title="Sin materias registradas"
                description="Aún no tenés materias en el padrón activo."
              />
            ) : (
              <MateriasCursadasTable materias={estado.materias} />
            )}
          </section>

          <section>
            <h2 className="text-[15px] font-bold text-ink mb-3">Coloquios reservados</h2>
            <ColoquiosReservadosPanel coloquios={estado.coloquios_reservados} />
          </section>
        </>
      )}
    </div>
  )
}
