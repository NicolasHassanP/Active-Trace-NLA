# activia-trace — Frontend

SPA built with React 18 + TypeScript, Vite, TanStack Query, React Hook Form + Zod, Axios and Tailwind CSS.

## Scripts

```bash
npm run dev          # Start Vite dev server (proxies /api → http://localhost:8000)
npm run build        # TypeScript check + Vite production build
npm run test         # Run all tests (Vitest + jsdom) once
npm run test:watch   # Run tests in watch mode
npm run test:coverage # Run tests with coverage report (≥80% lines required)
npm run typecheck    # TypeScript check without build
npm run lint         # ESLint (fails on `any` and other violations)
```

## Feature-based Structure

```
src/
  features/
    auth/
      types/         # AuthUser, AuthTokens, Role, JwtPayload
      services/      # authService.ts (login/logout/refresh), loginSchema.ts, decodeJwtPayload.ts
      hooks/         # AuthProvider, AuthContext, useAuth, useLogin, useLogout
      components/    # LoginPage
    shell/
      types/         # NavItem
      components/    # AppLayout, Sidebar, Topbar, buildNav (pure fn)
  shared/
    services/
      api.ts         # Axios instance + interceptors (request token, response 401 refresh)
      tokenStore.ts  # In-memory token storage (NO localStorage/sessionStorage)
    components/      # ProtectedRoute, NotFound404, Forbidden403, DashboardPlaceholder
  App.tsx            # Root: QueryClientProvider → BrowserRouter → AuthProvider → Routes
  main.tsx           # Entry point
```

## Auth Contract

### Backend endpoints consumed

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/login` | POST | Authenticate with email + password. Returns `{ access_token, refresh_token, token_type }`. Requires `X-Tenant` header (UUID). |
| `/api/v1/auth/refresh` | POST | Rotate refresh token. Body: `{ refresh_token }`. Returns new token pair. |
| `/api/v1/auth/logout` | POST | Revoke refresh session. Body: `{ refresh_token }`. |

### Token strategy

- **Access token**: stored **in memory only** via `tokenStore.ts` — never `localStorage` or `sessionStorage`.
- **Refresh token**: stored **in memory** as well (backend C-03 implementation uses body-based refresh, not httpOnly cookie).
- **Identity hydration**: the frontend decodes the JWT payload (Base64, no signature verification) to extract `sub`, `tenant_id`, `roles`, `exp`. No `GET /auth/me` endpoint exists (OQ-1 closed).
- **Auto-refresh**: Axios response interceptor intercepts `401`, calls `POST /auth/refresh`, retries original request once (flag `_retry`). Concurrent 401s share a single refresh promise.
- **Session rehydration on reload**: `AuthProvider` calls `POST /auth/refresh` on mount. If refresh is valid → session restored. If not → user must log in again.

### Environment variables

```
VITE_TENANT_ID=<tenant-uuid>   # Tenant UUID sent as X-Tenant header in login requests
```
