/**
 * Zod schema for creating a Tarea.
 * Mirrors TareaCreate backend validation (D4, D6 from C-16).
 * Task 3.5.
 *
 * Rules:
 *   - asignado_a: required non-empty string (UUID)
 *   - descripcion: required non-empty string
 *   - contexto_id + contexto_tipo: both null/undefined OR both present (coherence D4)
 *   - materia_id: optional nullable UUID string
 */
import { z } from 'zod'

export const tareaCreateSchema = z
  .object({
    asignado_a: z.string().min(1, { message: 'El docente asignado es obligatorio' }),
    descripcion: z.string().min(1, { message: 'La descripción es obligatoria' }),
    materia_id: z.string().nullable().optional(),
    contexto_id: z.string().nullable().optional(),
    contexto_tipo: z.string().nullable().optional(),
  })
  .superRefine((data, ctx) => {
    const hasId = data.contexto_id != null && data.contexto_id !== ''
    const hasTipo = data.contexto_tipo != null && data.contexto_tipo !== ''
    if (hasId !== hasTipo) {
      const field = hasId ? 'contexto_tipo' : 'contexto_id'
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'contexto_id y contexto_tipo deben ser ambos nulos o ambos presentes',
        path: [field],
      })
    }
  })

export type TareaCreateFormValues = z.infer<typeof tareaCreateSchema>
