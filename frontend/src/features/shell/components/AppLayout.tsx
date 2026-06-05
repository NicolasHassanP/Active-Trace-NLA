/**
 * AppLayout — root authenticated layout.
 *
 * Structure:
 *   +---topbar-------------------+
 *   | sidebar | content (Outlet) |
 *   +----------------------------+
 *
 * < 200 LOC, no `any`
 */
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppLayout() {
  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
