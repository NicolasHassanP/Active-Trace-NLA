/**
 * UsuarioCombobox — searchable combobox for selecting a user in asignacion create form.
 *
 * Replaces the raw UUID input for usuario_id in create mode.
 * Debounces input 300ms, queries GET /asignaciones/usuarios?q=...
 * Shows nombre + apellidos (email in monospace below for disambiguation).
 * On selection calls onChange(usuario.id) and shows selected name.
 * Clear button resets to unselected state.
 *
 * Props:
 *   value      — current usuario_id (string | null)
 *   onChange   — called with selected usuario_id or null
 *   error      — optional Zod validation error message
 *   searchHook — optional hook override for search (defaults to useBuscarUsuariosAsignables).
 *                Prop must be stable (set once at mount) — never toggle between hook
 *                implementations on the same instance (Rules of Hooks).
 *
 * < 200 LOC. No `any`. PascalCase. Tailwind only.
 */
import { useState, useEffect, useRef } from 'react'
import { useBuscarUsuariosAsignables } from '../hooks/asignacionHooks'
import type { UsuarioAsignable } from '../types'

export type SearchHook = (q: string) => { data?: UsuarioAsignable[]; isLoading?: boolean; isFetching?: boolean }

interface Props {
  value: string | null
  onChange: (id: string | null) => void
  error?: string
  /** Inject an alternative search hook (e.g. for a different endpoint).
   *  Defaults to useBuscarUsuariosAsignables. Must be stable — never switch
   *  hook implementations after mount (React Rules of Hooks). */
  searchHook?: SearchHook
}

const DEBOUNCE_MS = 300

export default function UsuarioCombobox({ value, onChange, error, searchHook }: Props) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<UsuarioAsignable | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Debounce the query
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [query])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // When a custom searchHook is injected it is called with the live query and
  // takes priority. The default hook is kept dormant (empty string — its
  // `enabled` guard keeps it from firing) so Rules of Hooks are satisfied.
  // IMPORTANT: searchHook must be stable at mount (never toggled per-instance).
  const defaultResult = useBuscarUsuariosAsignables(searchHook ? '' : debouncedQuery)
  const customResult = searchHook ? searchHook(debouncedQuery) : null
  const result = customResult ?? defaultResult
  const resultados: UsuarioAsignable[] = result.data ?? []
  const isFetching = result.isFetching ?? result.isLoading ?? false

  function handleSelect(usuario: UsuarioAsignable) {
    setSelected(usuario)
    onChange(usuario.id)
    setQuery('')
    setDebouncedQuery('')
    setOpen(false)
  }

  function handleClear() {
    setSelected(null)
    onChange(null)
    setQuery('')
    setDebouncedQuery('')
    setOpen(false)
  }

  const inputClass =
    'w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ' +
    (error ? 'border-red-500' : 'border-gray-300')

  // SELECTED STATE: show chip with name + clear button
  if (selected !== null && value !== null) {
    return (
      <div data-testid="usuario-combobox">
        <div className="flex items-center gap-2 rounded border border-gray-300 bg-gray-50 px-3 py-2 text-sm">
          <span className="flex-1 font-medium text-gray-800" data-testid="usuario-combobox-selected">
            {selected.nombre} {selected.apellidos}
          </span>
          <span className="font-mono text-xs text-gray-500">{selected.email}</span>
          <button
            type="button"
            onClick={handleClear}
            className="ml-2 rounded text-gray-400 hover:text-red-600 focus:outline-none"
            data-testid="usuario-combobox-clear"
            aria-label="Limpiar selección"
          >
            ✕
          </button>
        </div>
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </div>
    )
  }

  // SEARCH STATE: input + dropdown
  return (
    <div className="relative" ref={containerRef} data-testid="usuario-combobox">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => { if (query.trim().length >= 1) setOpen(true) }}
        placeholder="Buscar por nombre o apellidos…"
        className={inputClass}
        data-testid="usuario-combobox-input"
        autoComplete="off"
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}

      {open && debouncedQuery.trim().length >= 1 && (
        <ul
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded border border-gray-200 bg-white shadow-lg"
          data-testid="usuario-combobox-dropdown"
          role="listbox"
        >
          {isFetching && (
            <li className="px-3 py-2 text-sm text-gray-400" data-testid="usuario-combobox-loading">
              Buscando…
            </li>
          )}
          {!isFetching && resultados.length === 0 && (
            <li className="px-3 py-2 text-sm text-gray-400" data-testid="usuario-combobox-empty">
              Sin resultados para &ldquo;{debouncedQuery}&rdquo;
            </li>
          )}
          {resultados.map((u) => (
            <li
              key={u.id}
              role="option"
              aria-selected={false}
              className="cursor-pointer px-3 py-2 hover:bg-blue-50"
              onMouseDown={() => handleSelect(u)}
              data-testid={`usuario-option-${u.id}`}
            >
              <span className="font-medium text-gray-800">
                {u.apellidos}, {u.nombre}
              </span>
              <br />
              <span className="font-mono text-xs text-gray-500">{u.email}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
