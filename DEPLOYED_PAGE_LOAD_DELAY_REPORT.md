# Deployed Page Load Delay Report

## Summary

The deployed app is slower mainly because page rendering is blocked by production network round trips that do not exist, or are nearly invisible, on local development.

This is not caused by a single slow React component. The current production flow combines:

1. Client-only dashboard layouts.
2. Auth initialization that must complete before the dashboard renders.
3. Vercel route handlers calling the Railway backend.
4. Browser-to-Railway API calls with `Authorization` headers.
5. Many pages fetching their own data only after hydration.
6. No route-level `loading.tsx` fallbacks.

Facebook and other large apps feel instant because they aggressively pre-render shells, co-locate services, stream data, prefetch routes/data, keep global edge caches warm, and avoid blocking the first visible UI on several cross-service requests. Obelytics currently behaves more like a client-side app that waits for remote auth and remote data before showing the real workspace.

## Most Likely Causes

### 1. Dashboard UI is blocked by client-side auth initialization

Evidence:

- `frontend/components/auth-provider.tsx` runs auth initialization in a client `useEffect`.
- If there is no valid cached access token and persisted auth data, it calls `/api/auth/refresh`.
- After refresh, it calls `getMeApi(token)`.
- `frontend/app/(dashboard)/layout.tsx` does not render the dashboard shell until `isInitialized` is true.

Relevant files:

- `frontend/components/auth-provider.tsx`
- `frontend/app/(dashboard)/layout.tsx`
- `frontend/lib/api/auth.ts`

Current blocking path after access token expiry or first load:

```text
Browser loads page
  -> React hydrates
  -> AuthProvider runs
  -> POST /api/auth/refresh on Vercel
  -> Vercel function calls Railway backend /auth/refresh
  -> Browser calls Railway /users/me and /users/me/permissions
  -> Zustand auth state is filled
  -> Dashboard layout finally renders
  -> Page data queries start
```

Locally, these calls are near-zero latency because frontend, backend, database, and Redis are close. In production, each request crosses real networks.

### 2. Refresh/login uses a Vercel-to-Railway backend hop

Evidence:

- `frontend/app/api/auth/refresh/route.ts` calls `${BACKEND}/api/v1/auth/refresh`.
- `frontend/app/api/auth/login/route.ts` calls Railway login, then calls `users/me`, `users/me/permissions`, and `programs`.

This is necessary today because the refresh token is stored in an HttpOnly cookie on the frontend domain. But if the Vercel function region is far from the Railway backend region, every login/refresh inherits that distance.

### 3. Browser API calls go directly to Railway and usually trigger CORS preflight

Evidence:

- `frontend/lib/api/client.ts` sets `apiClient` base URL to `NEXT_PUBLIC_API_URL`.
- Every authenticated request includes `Authorization`.
- Some requests include `X-Program-Id`.

Authenticated cross-origin requests normally require an `OPTIONS` preflight before the real request. That means a simple page data call can become:

```text
OPTIONS https://railway-backend/api/v1/...
GET     https://railway-backend/api/v1/...
```

On local development this is cheap. On deployed Vercel + Railway it becomes visible.

### 4. CORS deployment documentation is inconsistent with backend parser

Evidence:

- `backend/app/core/config.py` parses `ALLOWED_ORIGINS` as a comma-separated string:

```python
return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
```

- `DEPLOYMENT.md` tells users to set it as a JSON array string:

```text
["https://YOUR-FRONTEND-DOMAIN.up.railway.app"]
```

That value will not parse into a clean origin. It can produce origins like:

```text
["https://YOUR-FRONTEND-DOMAIN.up.railway.app"]
```

instead of:

```text
https://YOUR-FRONTEND-DOMAIN.up.railway.app
```

If production CORS is misconfigured, direct browser calls can fail, retry, or behave inconsistently depending on the endpoint and browser cache.

### 5. Pages are mostly static shells plus client-side data loading

Evidence:

- Most dashboard `page.tsx` files render a client component.
- Most client pages call `useQuery` inside the browser.
- There are no `loading.tsx` files under `frontend/app`.

The production build succeeds, but route content depends on client bundles and client API calls. This is fine for internal dashboards, but it needs good loading states, prefetching, and a fast auth/session path.

### 6. Some routes issue many parallel API requests

Examples found:

- `course-outcomes-client.tsx` loads curricula, courses, POs, Bloom levels, Bloom domains, assignments, and COs.
- course detail and mapping pages load mapping sets, mapping entries, validation, and reference data.
- marksheet pages load sections, offering, assignments, outcomes, result, questions, and reports.

Parallel requests are better than serial requests, but in production many parallel cross-origin requests can still feel slow, especially when each one may have preflight overhead.

## What To Fix First

### Priority 1: Make auth bootstrap one fast same-origin request

Create a single frontend route handler:

```text
GET /api/auth/session
```

It should:

1. Read the HttpOnly `refresh_token` cookie.
2. Refresh the backend session if needed.
3. Fetch one backend bootstrap endpoint.
4. Return access token, user, permissions, programs, and offering IDs in one response.
5. Set the rotated refresh cookie and short-lived access cookie.

Then change `AuthProvider` to call only `/api/auth/session` when the local fast-path cache is missing.

Recommended backend endpoint:

```text
GET /api/v1/auth/session
```

or:

```text
GET /api/v1/users/me/bootstrap
```

Response shape:

```json
{
  "user": {},
  "permissions": [],
  "scope": {
    "programs": [],
    "is_global": false
  },
  "offering_ids": []
}
```

This removes the current refresh + `users/me` + `users/me/permissions` startup chain from the browser.

### Priority 2: Co-locate Vercel auth route handlers with Railway

For the auth route handlers, set a preferred region matching the Railway backend region.

Example:

```ts
export const runtime = "edge"
export const preferredRegion = "iad1"
```

Use the Vercel region nearest to the Railway service. If Railway is in US East, `iad1` is usually the right Vercel region. If Railway is in Europe or Asia, choose the nearest Vercel region accordingly.

Do this for:

- `frontend/app/api/auth/login/route.ts`
- `frontend/app/api/auth/refresh/route.ts`
- `frontend/app/api/auth/logout/route.ts`
- the proposed `frontend/app/api/auth/session/route.ts`

### Priority 3: Fix CORS env format

Set Railway backend variable as comma-separated origins, not JSON:

```text
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app,https://your-custom-domain.com,http://localhost:3000
```

Then update `DEPLOYMENT.md` so future deploys do not copy the wrong format.

Optional backend hardening:

```python
import json

@computed_field
@property
def ALLOWED_ORIGINS_LIST(self) -> list[str]:
    raw = self.ALLOWED_ORIGINS.strip()
    if raw.startswith("["):
        return [str(o).strip() for o in json.loads(raw) if str(o).strip()]
    return [o.strip() for o in raw.split(",") if o.strip()]
```

### Priority 4: Add route-level loading states

Add `loading.tsx` files for route groups:

```text
frontend/app/(dashboard)/loading.tsx
frontend/app/(student)/loading.tsx
```

Also add focused loading files for heavy routes:

```text
frontend/app/(dashboard)/courses/[id]/loading.tsx
frontend/app/(dashboard)/my-sections/[id]/loading.tsx
frontend/app/(dashboard)/result-submissions/loading.tsx
frontend/app/(dashboard)/attainment/loading.tsx
```

This will not make APIs faster, but it prevents the app from feeling frozen.

### Priority 5: Reduce page request count

For heavy pages, add backend aggregate endpoints that return the exact page bootstrap payload.

Examples:

```text
GET /api/v1/pages/course-outcomes/bootstrap
GET /api/v1/pages/marksheet/{section_offering_id}/bootstrap
GET /api/v1/pages/curriculum/{id}/bootstrap
```

Do not overdo this for every page. Start with the pages that feel slowest in production.

### Priority 6: Improve prefetching

Current sidebar prefetching only happens on `onMouseEnter` and only for a few routes.

Recommended:

- Use `router.prefetch(href)` for visible nav items after auth initialization.
- Keep React Query data prefetch for the top 5 most-used routes.
- Avoid prefetching everything for every user; use permissions and current nav group.

## Deployment Checks

Run these checks against production:

```bash
curl -I https://YOUR-BACKEND/health/live
curl -I https://YOUR-BACKEND/health/ready
curl -I -X OPTIONS https://YOUR-BACKEND/api/v1/users/me \
  -H "Origin: https://YOUR-FRONTEND" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization,x-program-id"
```

Check that the OPTIONS response includes:

```text
access-control-allow-origin: https://YOUR-FRONTEND
access-control-allow-credentials: true
```

In the browser DevTools Network tab, measure:

- Time for `/api/auth/refresh`.
- Time for `/api/v1/users/me`.
- Time for `/api/v1/users/me/permissions`.
- Whether each API call has a preceding `OPTIONS`.
- Whether Vercel functions show cold starts.
- Whether the Railway backend logs show slow `X-Process-Time` or the delay is mostly network.

If backend `X-Process-Time` is low but browser request duration is high, the main issue is network topology/preflight/cold start, not SQL query time.

## Recommended Implementation Order

1. Fix `ALLOWED_ORIGINS` in Railway and deployment docs.
2. Add `/api/auth/session` and a backend bootstrap endpoint.
3. Change `AuthProvider` to use the single session endpoint.
4. Set Vercel auth route region close to Railway.
5. Add `(dashboard)/loading.tsx` and `(student)/loading.tsx`.
6. Profile production Network tab.
7. Add page bootstrap endpoints only for the slowest pages.

## Expected Result

After priority 1 through 5:

- Reloading a logged-in dashboard should show the app shell much faster.
- Expired-token reloads should require one same-origin session request instead of a multi-hop chain.
- Page navigation should feel responsive because the shell remains visible and route loading states appear immediately.
- Production performance should become much closer to local, while still depending on real API latency for page data.

