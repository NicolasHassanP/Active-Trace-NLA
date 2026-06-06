import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppLayout() {
  return (
    <div className="flex h-screen" style={{ background: '#f7f8fb' }}>
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto" style={{ padding: '24px 28px 40px' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
