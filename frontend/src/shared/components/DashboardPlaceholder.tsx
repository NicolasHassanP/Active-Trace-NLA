/**
 * DashboardPlaceholder — temporary landing page.
 * Will be replaced by C-22/C-23/C-24 feature routes.
 */
export default function DashboardPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <h1 className="text-2xl font-bold text-gray-800">Bienvenido a activia-trace</h1>
      <p className="mt-2 text-gray-500">
        Seleccioná una sección en el menú lateral para comenzar.
      </p>
    </div>
  )
}
