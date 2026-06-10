/**
 * SetupCuatrimestrePage — orchestrator wizard for semester setup.
 * RBAC: COORDINADOR and ADMIN only (FL-03).
 * Sequential steps, error blocks advance, completion shows success.
 * Tasks 7.11. < 200 LOC. Strict TDD.
 */
import { useAuth } from '@/features/auth/hooks/useAuth'
import Forbidden403 from '@/shared/components/Forbidden403'
import SetupStepper from '../components/SetupStepper'
import PasoCohorte from '../components/PasoCohorte'
import PasoClonarEquipo from '../components/PasoClonarEquipo'
import PasoAsignaciones from '../components/PasoAsignaciones'
import PasoVigencias from '../components/PasoVigencias'
import PasoProgramas from '../components/PasoProgramas'
import PasoFechas from '../components/PasoFechas'
import PasoAvisoBienvenida from '../components/PasoAvisoBienvenida'
import { useSetupWizard } from '../hooks/useSetupWizard'
import type { Role } from '@/features/auth/types'
import { PageHeader } from '@/shared/components/ui'

const ALLOWED_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function SetupCuatrimestrePage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  if (!isAllowed) {
    return <Forbidden403 />
  }

  return <SetupWizard />
}

/**
 * Inner wizard component — separated so role check comes first (fail-closed).
 * The wizard renders one step panel at a time in sequence.
 */
function SetupWizard() {
  const { state, completeStep, errorStep, retryStep: _retry } = useSetupWizard()
  const { pasos, pasoActivo, completado } = state

  if (completado) {
    return (
      <div
        className="max-w-2xl mx-auto p-8 text-center space-y-4"
        data-testid="setup-completado"
      >
        <div className="text-green-600 text-5xl">✓</div>
        <h1 className="text-2xl font-bold text-gray-900">
          ¡Cuatrimestre configurado!
        </h1>
        <p className="text-gray-600">
          Todos los pasos del setup se completaron correctamente.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-8">
      {/* Left panel: stepper */}
      <aside className="col-span-1">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Progreso
        </h2>
        <SetupStepper pasos={pasos} pasoActivo={pasoActivo} />
      </aside>

      {/* Right panel: active step form */}
      <main className="col-span-2 space-y-4">
        <PageHeader title="Setup de cuatrimestre" />

        {pasoActivo === 0 && (
          <PasoCohorte
            onSuccess={(id) => {
              void id
              completeStep(0)
            }}
            onError={(msg) => errorStep(0, msg)}
          />
        )}
        {pasoActivo === 1 && (
          <PasoClonarEquipo
            onSuccess={() => completeStep(1)}
            onError={(msg) => errorStep(1, msg)}
          />
        )}
        {pasoActivo === 2 && (
          <PasoAsignaciones
            onSuccess={() => completeStep(2)}
            onError={(msg) => errorStep(2, msg)}
          />
        )}
        {pasoActivo === 3 && (
          <PasoVigencias
            onSuccess={() => completeStep(3)}
            onError={(msg) => errorStep(3, msg)}
          />
        )}
        {pasoActivo === 4 && (
          <PasoProgramas
            onSuccess={() => completeStep(4)}
            onError={(msg) => errorStep(4, msg)}
          />
        )}
        {pasoActivo === 5 && (
          <PasoFechas
            onSuccess={() => completeStep(5)}
            onError={(msg) => errorStep(5, msg)}
          />
        )}
        {pasoActivo === 6 && (
          <PasoAvisoBienvenida
            onSuccess={() => completeStep(6)}
            onError={(msg) => errorStep(6, msg)}
          />
        )}
      </main>
    </div>
  )
}
