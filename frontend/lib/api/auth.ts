import type { MeResponse, UserProfile, PermissionManifest } from "@/types"
import { fetchWithTimeout } from "@/lib/api/client"

// Client-side calls use NEXT_PUBLIC_API_URL to call the backend directly (no proxy hop).
// Server-side BFF routes use BACKEND_URL env var directly.

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// Login goes through the BFF so it can set the HttpOnly refresh_token cookie
export async function loginApi(email: string, password: string): Promise<{
  access_token: string
  user: UserProfile
  permissions: string[]
  scope: PermissionManifest["scope"]
  offering_ids: string[]
}> {
  const res = await fetchWithTimeout("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "Login failed" }))
    throw new Error(err.message ?? "Login failed")
  }
  return res.json()
}

export async function sessionApi(): Promise<{
  access_token: string
  user: UserProfile
  permissions: string[]
  scope: PermissionManifest["scope"]
  offering_ids: string[]
}> {
  const res = await fetchWithTimeout("/api/auth/session", {
    method: "POST",
    credentials: "include",
  })
  if (!res.ok) throw new Error("no_session")
  return res.json()
}

// Used by AuthProvider after silent refresh — calls backend directly with the new access token
export async function getMeApi(accessToken: string): Promise<MeResponse> {
  const [meRes, permsRes] = await Promise.all([
    fetchWithTimeout(`${PUBLIC_API_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      credentials: "include",
    }),
    fetchWithTimeout(`${PUBLIC_API_URL}/api/v1/users/me/permissions`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      credentials: "include",
    }),
  ])

  if (!meRes.ok) throw new Error("Failed to fetch user profile")
  if (!permsRes.ok) throw new Error("Failed to fetch permissions")

  const me = await meRes.json()
  const perms = await permsRes.json()

  const fullName: string = me.full_name ?? ""
  const spaceIdx = fullName.indexOf(" ")
  const firstName = spaceIdx > 0 ? fullName.slice(0, spaceIdx) : fullName
  const lastName = spaceIdx > 0 ? fullName.slice(spaceIdx + 1) : ""

  return {
    id: String(me.id),
    email: me.email,
    full_name: fullName,
    first_name: firstName,
    last_name: lastName,
    employee_id: me.employee_id ?? "",
    faculty_type: me.faculty_type ?? "",
    status: me.status ?? "ACTIVE",
    department: me.department ?? null,
    permissions: perms.permissions ?? [],
    scope: {
      programs: [],  // programs not fetched here; populated on login
      is_global: perms.is_super_admin ?? false,
    },
    offering_ids: perms.offering_ids ?? [],
  }
}

export async function logoutApi(accessToken: string) {
  // Clear the HttpOnly refresh_token cookie via BFF
  await fetchWithTimeout("/api/auth/logout", { method: "POST", credentials: "include" }).catch(() => {})
  // Also tell the backend to revoke the token (best-effort)
  await fetchWithTimeout(`${PUBLIC_API_URL}/api/v1/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: "include",
  }).catch(() => {})
}

export async function requestPasswordReset(email: string) {
  const res = await fetchWithTimeout(`${PUBLIC_API_URL}/api/v1/auth/password-reset-request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) throw new Error("Request failed")
}

export async function confirmPasswordReset(token: string, password: string) {
  const res = await fetchWithTimeout(`${PUBLIC_API_URL}/api/v1/auth/password-reset-confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "Reset failed" }))
    throw new Error(err.message ?? "Reset failed")
  }
}
