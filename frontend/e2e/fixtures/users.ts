/**
 * Demo users for the Demo tenant (8531f634-3f1f-45da-9549-2f801d85c39b).
 * Credentials match backend/seed_demo_users.py and DemoUserPicker.tsx.
 *
 * Note: a TUTOR user (Carlos Mendez) also exists in seed/picker but is not
 * part of the required E2E coverage. There is intentionally NO FINANZAS user.
 */
export type DemoRole = 'COORDINADOR' | 'PROFESOR' | 'ALUMNO' | 'ADMIN'

export interface DemoUser {
  role: DemoRole
  email: string
  password: string
}

export const DEMO_USERS: Record<DemoRole, DemoUser> = {
  COORDINADOR: { role: 'COORDINADOR', email: 'coordinador@demo.com', password: 'Demo1234!' },
  PROFESOR: { role: 'PROFESOR', email: 'profesor@demo.com', password: 'Demo1234!' },
  ALUMNO: { role: 'ALUMNO', email: 'alumno@demo.com', password: 'Demo1234!' },
  ADMIN: { role: 'ADMIN', email: 'admin@demo.com', password: 'Admin1234!' },
}
