/**
 * PasoCohorte — Step 1: Select or create the cohorte for the new cuatrimestre.
 * Task 7.4. < 200 LOC.
 *
 * UX: A <select> list existing cohortes (by nombre). A toggle button reveals a
 * mini-form (RHF + Zod) to POST a new cohorte. On creation success the list is
 * refreshed via TanStack Query invalidation and the new cohorte is auto-selected.
 */
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/shared/components/ui'
import {
  listarTodosCohortes,
  listarTodasCarreras,
  crearCohorte,
  type CohorteCreatePayload,
} from '@/features/monitores/services/monitoresService'
import { toast } from 'sonner'

// ── Main select schema ──────────────────────────────────────────────────────

const selectSchema = z.object({
  cohorte_id: z.string().min(1, 'Seleccioná una cohorte'),
  nombre: z.string().min(1),
})

type SelectFormValues = z.infer<typeof selectSchema>

// ── Create cohorte mini-form schema ────────────────────────────────────────

const crearCohorteSchema = z.object({
  carrera_id: z.string().min(1, 'Seleccioná una carrera'),
  nombre: z.string().min(1, 'El nombre es requerido'),
  anio: z
    .number({ invalid_type_error: 'El año debe ser un número' })
    .int()
    .min(2000, 'Año inválido')
    .max(2100, 'Año inválido'),
  vig_desde: z.string().min(1, 'La fecha de inicio es requerida'),
  vig_hasta: z.string().nullable().optional(),
})

type CrearCohorteFormValues = z.infer<typeof crearCohorteSchema>

// ── useCrearCohorte mutation hook ──────────────────────────────────────────

function useCrearCohorte() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CohorteCreatePayload) => crearCohorte(payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['admin-cohortes'] })
    },
  })
}

// ── Component ──────────────────────────────────────────────────────────────

interface PasoCohorteProps {
  onSuccess: (cohorteId: string) => void
  onError: (msg: string) => void
}

export default function PasoCohorte({ onSuccess, onError: _onError }: PasoCohorteProps) {
  const [showCrear, setShowCrear] = useState(false)

  // ── Select existing cohorte form ────────────────────────────────────────
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SelectFormValues>({ resolver: zodResolver(selectSchema) })

  const cohortesQuery = useQuery({ queryKey: ['admin-cohortes'], queryFn: listarTodosCohortes })
  const carrerasQuery = useQuery({ queryKey: ['admin-carreras'], queryFn: listarTodasCarreras })
  const cohortes = cohortesQuery.data ?? []
  const carreras = carrerasQuery.data ?? []

  const selectedNombre = watch('nombre')

  function handleSelect(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value
    const cohorte = cohortes.find((c) => c.id === id)
    setValue('nombre', cohorte?.nombre ?? '', { shouldValidate: true })
  }

  function onSubmit(data: SelectFormValues) {
    onSuccess(data.cohorte_id)
  }

  // ── Create cohorte mini-form ────────────────────────────────────────────
  const crearMutation = useCrearCohorte()

  const {
    register: regCrear,
    handleSubmit: handleCrear,
    reset: resetCrear,
    formState: { errors: crearErrors, isSubmitting: crearSubmitting },
  } = useForm<CrearCohorteFormValues>({
    resolver: zodResolver(crearCohorteSchema),
    defaultValues: { anio: new Date().getFullYear(), vig_hasta: null },
  })

  async function onCrear(data: CrearCohorteFormValues) {
    const result = await crearMutation.mutateAsync({
      carrera_id: data.carrera_id,
      nombre: data.nombre,
      anio: data.anio,
      vig_desde: data.vig_desde,
      vig_hasta: data.vig_hasta ?? null,
    })
    // Auto-select the newly created cohorte in the main form
    setValue('cohorte_id', result.id, { shouldValidate: true })
    setValue('nombre', result.nombre, { shouldValidate: true })
    toast.success(`Cohorte "${result.nombre}" creada y seleccionada`)
    resetCrear()
    setShowCrear(false)
  }

  return (
    <div className="space-y-4" data-testid="paso-cohorte">
      {/* ── Select existing cohorte ─────────────────────────────────────── */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <p className="text-sm text-gray-600">
          Seleccioná la cohorte de este cuatrimestre o creá una nueva.
        </p>

        <div>
          <label className="block text-sm font-medium text-gray-700">Cohorte</label>
          <select
            {...register('cohorte_id', { onChange: handleSelect })}
            data-testid="cohorte-id"
            disabled={cohortesQuery.isLoading}
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">
              {cohortesQuery.isLoading ? 'Cargando…' : '-- Seleccioná una cohorte --'}
            </option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {errors.cohorte_id && (
            <p className="mt-1 text-xs text-red-600">{errors.cohorte_id.message}</p>
          )}
        </div>

        <input type="hidden" {...register('nombre')} />
        {selectedNombre && (
          <p className="text-sm text-gray-600">
            Período: <span className="font-medium text-gray-800">{selectedNombre}</span>
          </p>
        )}

        <div className="flex items-center gap-3">
          <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
            {isSubmitting ? 'Guardando…' : 'Confirmar cohorte'}
          </Button>
          <button
            type="button"
            onClick={() => setShowCrear((v) => !v)}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-800 underline"
          >
            {showCrear ? 'Cancelar nueva cohorte' : '+ Crear nueva cohorte'}
          </button>
        </div>
      </form>

      {/* ── Create cohorte mini-form ─────────────────────────────────────── */}
      {showCrear && (
        <form
          onSubmit={handleCrear(onCrear)}
          data-testid="crear-cohorte-form"
          className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3"
        >
          <h3 className="text-sm font-semibold text-indigo-800">Nueva cohorte</h3>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-700">Carrera</label>
              <select
                {...regCrear('carrera_id')}
                disabled={carrerasQuery.isLoading}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <option value="">
                  {carrerasQuery.isLoading ? 'Cargando…' : '-- Seleccioná --'}
                </option>
                {carreras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
              {crearErrors.carrera_id && (
                <p className="mt-0.5 text-xs text-red-600">{crearErrors.carrera_id.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">Nombre</label>
              <input
                type="text"
                {...regCrear('nombre')}
                placeholder="Ej: 2025-1"
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              {crearErrors.nombre && (
                <p className="mt-0.5 text-xs text-red-600">{crearErrors.nombre.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">Año</label>
              <input
                type="number"
                {...regCrear('anio', { valueAsNumber: true })}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              {crearErrors.anio && (
                <p className="mt-0.5 text-xs text-red-600">{crearErrors.anio.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">Vigencia desde</label>
              <input
                type="date"
                {...regCrear('vig_desde')}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              {crearErrors.vig_desde && (
                <p className="mt-0.5 text-xs text-red-600">{crearErrors.vig_desde.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">
                Vigencia hasta{' '}
                <span className="text-gray-400 font-normal">(opcional)</span>
              </label>
              <input
                type="date"
                {...regCrear('vig_hasta')}
                className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={crearSubmitting}
              isLoading={crearSubmitting}
            >
              {crearSubmitting ? 'Creando…' : 'Crear cohorte'}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
