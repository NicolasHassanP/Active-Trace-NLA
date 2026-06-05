import { z } from 'zod'

/**
 * Zod schema for the login form.
 * Validates email format and requires a non-empty password.
 */
export const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

export type LoginFormValues = z.infer<typeof loginSchema>
