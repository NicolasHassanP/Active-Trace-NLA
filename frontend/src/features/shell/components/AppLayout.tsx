import { useCallback } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '@/features/auth/hooks/useAuth'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

function ImpersonationBanner() {
  const { impersonatedName, finalizarImpersonacion } = useAuth()
  const navigate = useNavigate()

  const handleFinalizar = useCallback(async () => {
    try {
      await finalizarImpersonacion()
      navigate('/dashboard')
    } catch {
      toast.error('No se pudo finalizar la impersonación')
    }
  }, [finalizarImpersonacion, navigate])

  return (
    <div className="bg-amber-500 text-white px-6 py-2 flex items-center justify-between text-sm font-semibold">
      <span>Estás viendo como {impersonatedName}</span>
      <button
        type="button"
        onClick={() => { void handleFinalizar() }}
        className="border border-white text-white rounded px-3 py-1 text-sm font-semibold hover:bg-amber-600 transition-colors"
      >
        Finalizar impersonación
      </button>
    </div>
  )
}

export default function AppLayout() {
  const { isImpersonating } = useAuth()

  return (
    <div className="flex h-screen" style={{ background: '#f7f8fb' }}>
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        {isImpersonating && <ImpersonationBanner />}
        <Topbar />
        <main className="flex-1 overflow-y-auto" style={{ padding: '24px 28px 40px' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
