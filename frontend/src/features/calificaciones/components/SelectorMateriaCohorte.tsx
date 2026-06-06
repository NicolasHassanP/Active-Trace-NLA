/**
 * SelectorMateriaCohorte — free-text inputs for materia_id × cohorte_id.
 * Mirrors the PadronPage pattern: no catalog API (out of scope for this change).
 */
interface Props {
  materiaId: string
  cohorteId: string
  onMateriaChange: (v: string) => void
  onCohorteChange: (v: string) => void
}

export default function SelectorMateriaCohorte({
  materiaId,
  cohorteId,
  onMateriaChange,
  onCohorteChange,
}: Props) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">ID de Materia</label>
          <input
            type="text"
            value={materiaId}
            onChange={(e) => onMateriaChange(e.target.value)}
            placeholder="ej. uuid-materia"
            className="w-full border rounded px-3 py-2 text-sm"
            data-testid="materia-id-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">ID de Cohorte</label>
          <input
            type="text"
            value={cohorteId}
            onChange={(e) => onCohorteChange(e.target.value)}
            placeholder="ej. uuid-cohorte"
            className="w-full border rounded px-3 py-2 text-sm"
            data-testid="cohorte-id-input"
          />
        </div>
      </div>
    </section>
  )
}
