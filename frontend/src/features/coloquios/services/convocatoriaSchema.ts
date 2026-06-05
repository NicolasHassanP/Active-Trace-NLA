/**
 * convocatoriaSchema — Zod validation schema for creating a convocatoria.
 * Task 6.8.
 * Constraints:
 *   - cupo_total > 0 (backend validates this too, but we gate client-side)
 *   - dias_disponibles > 0 (días disponibles must be present and positive)
 *   - instancia must be non-empty
 *   - turnos must have at least one item
 */
import { z } from 'zod'

const turnoSchema = z.object({
  fecha: z.string().min(1, 'La fecha es requerida'),
  cupo_total: z.number({ invalid_type_error: 'cupo_total debe ser un número' })
    .int()
    .min(1, 'cupo_total debe ser mayor a 0'),
  franja: z.string().nullable().optional(),
})

export const convocatoriaSchema = z.object({
  materia_id: z.string().min(1, 'materia_id es requerido'),
  cohorte_id: z.string().min(1, 'cohorte_id es requerido'),
  tipo: z.enum(['coloquio', 'examen', 'parcial'], {
    errorMap: () => ({ message: 'tipo inválido' }),
  }),
  instancia: z.string().min(1, 'La instancia es requerida'),
  dias_disponibles: z.number({ invalid_type_error: 'dias_disponibles debe ser un número' })
    .int()
    .min(1, 'dias_disponibles debe ser mayor a 0'),
  turnos: z.array(turnoSchema).min(1, 'Debe haber al menos un turno'),
})

export type ConvocatoriaFormValues = z.infer<typeof convocatoriaSchema>
