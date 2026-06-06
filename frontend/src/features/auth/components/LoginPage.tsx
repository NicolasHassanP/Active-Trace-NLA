import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useLocation } from 'react-router-dom'
import { loginSchema, type LoginFormValues } from '../services/loginSchema'
import { useLogin } from '../hooks/useLogin'
import { useAuth } from '../hooks/useAuth'
import { DemoUserPicker } from './DemoUserPicker'

const TENANT_ID = import.meta.env.VITE_TENANT_ID as string || '8531f634-3f1f-45da-9549-2f801d85c39b'

export default function LoginPage() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const { isAuthenticated } = useAuth()
  const loginMutation = useLogin()

  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, location.state])

  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } =
    useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

  const doLogin = async (email: string, password: string) => {
    loginMutation.reset()
    await loginMutation.mutateAsync({ email, password, tenantId: TENANT_ID })
      .then(() => {
        const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'
        navigate(from, { replace: true })
      })
      .catch(() => {})
  }

  const onSubmit = async (values: LoginFormValues) => doLogin(values.email, values.password)

  const handleDemoSelect = (email: string, password: string) => {
    setValue('email', email)
    setValue('password', password)
    doLogin(email, password)
  }

  const isPending = isSubmitting || loginMutation.isPending

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: '#f7f8fb' }}>
      <div className="w-full max-w-sm">

        {/* Card */}
        <div
          className="bg-white rounded-[20px] border border-line px-[32px] pt-[32px] pb-[28px]"
          style={{ boxShadow: '0 8px 26px rgba(16,24,40,.09)' }}
        >
          {/* Brand */}
          <div className="flex items-center gap-[10px] mb-[28px]">
            <div
              className="w-[32px] h-[32px] rounded-[9px] shrink-0"
              style={{
                background: 'linear-gradient(150deg,#6366f1,#4338ca)',
                boxShadow: '0 3px 8px rgba(67,56,202,.35)',
              }}
            />
            <span className="text-[17px] font-extrabold text-ink tracking-[-0.3px]">activia-trace</span>
          </div>

          <h2 className="text-[22px] font-extrabold text-ink tracking-[-0.6px]">Ingresar</h2>
          <p className="text-[13.5px] text-mut mt-1 mb-[22px]">Usá tu cuenta institucional</p>

          {/* Error */}
          {loginMutation.isError && (
            <div className="rounded-[10px] bg-warnBg border border-warn/20 px-[14px] py-[10px] mb-[16px]">
              <p className="text-[13px] text-warn font-semibold">Email o contraseña incorrectos</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-[14px]" noValidate>
            <div>
              <label htmlFor="email" className="block text-[11.5px] font-bold text-[#3a4253] mb-[5px]">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                {...register('email')}
                className="w-full rounded-[10px] border border-line px-[12px] py-[9px] text-[13px] text-ink placeholder:text-faint focus:border-ind focus:outline-none focus:ring-1 focus:ring-ind transition-colors"
                placeholder="usuario@institución.edu"
                aria-describedby={errors.email ? 'email-error' : undefined}
              />
              {errors.email && (
                <p id="email-error" className="mt-1 text-[12px] text-warn" role="alert">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-[11.5px] font-bold text-[#3a4253] mb-[5px]">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
                className="w-full rounded-[10px] border border-line px-[12px] py-[9px] text-[13px] text-ink placeholder:text-faint focus:border-ind focus:outline-none focus:ring-1 focus:ring-ind transition-colors"
                placeholder="••••••••"
                aria-describedby={errors.password ? 'password-error' : undefined}
              />
              {errors.password && (
                <p id="password-error" className="mt-1 text-[12px] text-warn" role="alert">
                  {errors.password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="w-full flex justify-center items-center py-[10px] px-[14px] rounded-[10px] text-[13px] font-bold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: '#4338ca',
                boxShadow: '0 3px 8px rgba(67,56,202,.35)',
              }}
            >
              {isPending ? 'Ingresando…' : 'Ingresar'}
            </button>
          </form>

          {/* Demo user picker */}
          <DemoUserPicker onSelect={handleDemoSelect} loading={isPending} />
        </div>
      </div>
    </div>
  )
}
