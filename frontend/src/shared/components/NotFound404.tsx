/**
 * NotFound404 — 404 Not Found screen.
 */
import { Link } from 'react-router-dom'

export default function NotFound404() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-400">404</h1>
        <h2 className="mt-4 text-2xl font-semibold text-gray-900">Página no encontrada</h2>
        <p className="mt-2 text-gray-600">
          La ruta que buscás no existe en esta aplicación.
        </p>
        <Link
          to="/dashboard"
          className="mt-6 inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  )
}
