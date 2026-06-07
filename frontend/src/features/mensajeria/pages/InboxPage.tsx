import { useState } from 'react'
import { PageHeader } from '@/shared/components/ui/PageHeader'
import { Button } from '@/shared/components/ui/Button'
import { Card } from '@/shared/components/ui/Card'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { HilosList } from '../components/HilosList'
import { HiloView } from '../components/HiloView'
import { NuevoHiloForm } from '../components/NuevoHiloForm'
import { ResponderForm } from '../components/ResponderForm'
import { useHilos, useHilo } from '../hooks/mensajeriaHooks'

export default function InboxPage() {
  const [selectedHiloId, setSelectedHiloId] = useState<string | null>(null)
  const [showNuevoForm, setShowNuevoForm] = useState(false)

  const { data: hilos = [], isLoading: hilosLoading } = useHilos()
  const { data: mensajes = [], isLoading: mensajesLoading } = useHilo(selectedHiloId)

  const handleSelectHilo = (hiloId: string) => {
    setSelectedHiloId(hiloId)
    setShowNuevoForm(false)
  }

  const handleNuevoSuccess = () => {
    setShowNuevoForm(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mensajes"
        subtitle="Bandeja de mensajería interna"
        actions={
          <Button size="sm" onClick={() => { setShowNuevoForm(true); setSelectedHiloId(null) }}>
            Nuevo mensaje
          </Button>
        }
      />

      <div className="grid grid-cols-[280px_1fr] gap-5 h-[calc(100vh-220px)]">
        {/* Panel izquierdo — lista de hilos */}
        <Card className="overflow-y-auto p-0">
          {hilosLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-ind" />
            </div>
          ) : (
            <HilosList
              hilos={hilos}
              selectedHiloId={selectedHiloId}
              onSelect={handleSelectHilo}
            />
          )}
        </Card>

        {/* Panel derecho — hilo activo o form nuevo */}
        <Card className="flex flex-col p-0 overflow-hidden">
          {showNuevoForm ? (
            <NuevoHiloForm
              onSuccess={handleNuevoSuccess}
              onCancel={() => setShowNuevoForm(false)}
            />
          ) : selectedHiloId ? (
            <>
              <div className="flex-1 overflow-y-auto px-4">
                <HiloView mensajes={mensajes} isLoading={mensajesLoading} />
              </div>
              <ResponderForm
                hiloId={selectedHiloId}
                onSuccess={() => {}}
              />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState
                title="Seleccioná un hilo"
                description="Elegí una conversación de la lista o iniciá un mensaje nuevo."
              />
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
