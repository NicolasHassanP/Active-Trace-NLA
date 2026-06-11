import type { Role } from '@/features/auth/types'

/**
 * Navigation item in the sidebar.
 * `roles` lists which roles can see this item (empty = visible to all authenticated users).
 * `disabled` marks an item as visible but not navigable (e.g. "Próximamente").
 */
export interface NavItem {
  label: string
  path: string
  roles: Role[]
  icon?: string
  group?: string
  disabled?: boolean
}
