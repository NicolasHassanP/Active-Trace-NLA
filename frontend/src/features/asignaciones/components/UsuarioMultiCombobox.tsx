/**
 * UsuarioMultiCombobox — multi-select searchable combobox for selecting multiple users.
 *
 * Reuses the same search pattern as UsuarioCombobox.
 * Selected users are shown as removable chips.
 * Debounces input 300ms, queries GET /asignaciones/usuarios?q=...
 *
 * Props:
 *   value      — current list of usuario_ids (string[])
 *   onChange   — called with updated array of ids
 *   error      — optional Zod validation error message
 *   searchHook — optional hook override for search (defaults to useBuscarUsuariosAsignables).
 *                Must be stable at mount (Rules of Hooks).
 *
 * < 200 LOC. No `any`. PascalCase. Tailwind only.
 */
import { useState, useEffect, useRef } from 'react'
import { useBuscarUsuariosAsignables } from '../hooks/asignacionHooks'
import type { UsuarioAsignable } from '../types'
import type { SearchHook } from './UsuarioCombobox'

interface Props {
  value: string[]
  onChange: (ids: string[]) => void
  error?: string
  searchHook?: SearchHook
}

const DEBOUNCE_MS = 300

export default function UsuarioMultiCombobox({ value, onChange, error, searchHook }: Props) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [open, setOpen] = useState(false)
  // Map of id → UsuarioAsignable for rendering chips
  const [selectedMap, setSelectedMap] = useState<Map<string, UsuarioAsignable>>(new Map())
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

  // Same hook resolution pattern as UsuarioCombobox — always call default hook.
  const defaultResult = useBuscarUsuariosAsignables(searchHook ? '' : debouncedQuery)
  const customResult = searchHook ? searchHook(debouncedQuery) : null
  const result = customResult ?? defaultResult
  const resultados: UsuarioAsignable[] = result.data ?? []
  const isFetching = result.isFetching ?? result.isLoading ?? false

  // Only show results not already selected
  const filteredResultados = resultados.filter((u) => !value.includes(u.id))

  function handleSelect(usuario: UsuarioAsignable) {
    if (value.includes(usuario.id)) return
    const next = new Map(selectedMap)
    next.set(usuario.id, usuario)
    setSelectedMap(next)
    onChange([...value, usuario.id])
    setQuery('')
    setDebouncedQuery('')
    setOpen(false)
  }

  function handleRemove(id: string) {
    const next = new Map(selectedMap)
    next.delete(id)
    setSelectedMap(next)
    onChange(value.filter((v) => v !== id))
  }

  const inputClass =
    'flex-1 min-w-[8rem] rounded border-0 px-2 py-1 text-sm focus:outline-none focus:ring-0 ' +
    'bg-transparent placeholder:text-gray-400'

  const containerClass =
    'flex flex-wrap gap-1 rounded border px-2 py-1 focus-within:ring-2 focus-within:ring-blue-500 ' +
    (error ? 'border-red-500' : 'border-gray-300')

  return (
    <div className="relative" ref={containerRef} data-testid="usuario-multi-combobox">
      <div className={containerClass}>
        {/* Chips for selected users */}
        {value.map((id) => {
          const u = selectedMap.get(id)
          const label = u ? `${u.apellidos}, ${u.nombre}` : id.slice(0, 8) + '…'
          return (
            <span
              key={id}
              className="inline-flex items-center gap-1 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800"
              data-testid={`multi-chip-${id}`}
            >
              {label}
              <button
                type="button"
                onClick={() => handleRemove(id)}
                className="text-blue-500 hover:text-red-600 focus:outline-none"
                data-testid={`multi-chip-remove-${id}`}
                aria-label={`Quitar ${label}`}
              >
                ✕
              </button>
            </span>
          )
        })}

        {/* Search input */}
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => { if (query.trim().length >= 1) setOpen(true) }}
          placeholder={value.length === 0 ? 'Buscar usuarios…' : 'Agregar más…'}
          className={inputClass}
          data-testid="usuario-multi-combobox-input"
          autoComplete="off"
        />
      </div>

      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}

      {open && debouncedQuery.trim().length >= 1 && (
        <ul
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded border border-gray-200 bg-white shadow-lg"
          data-testid="usuario-multi-combobox-dropdown"
          role="listbox"
        >
          {isFetching && (
            <li className="px-3 py-2 text-sm text-gray-400" data-testid="usuario-multi-combobox-loading">
              Buscando…
            </li>
          )}
          {!isFetching && filteredResultados.length === 0 && (
            <li className="px-3 py-2 text-sm text-gray-400" data-testid="usuario-multi-combobox-empty">
              Sin resultados para &ldquo;{debouncedQuery}&rdquo;
            </li>
          )}
          {filteredResultados.map((u) => (
            <li
              key={u.id}
              role="option"
              aria-selected={false}
              className="cursor-pointer px-3 py-2 hover:bg-blue-50"
              onMouseDown={() => handleSelect(u)}
              data-testid={`usuario-multi-option-${u.id}`}
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
