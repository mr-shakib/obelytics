import { NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface BootstrapProgram {
  id: string
  name: string
  acronym: string
}

interface BootstrapUser {
  id: string
  email: string
  full_name: string
  first_name?: string | null
  last_name?: string | null
  employee_id?: string | null
  faculty_type?: string | null
  title?: string | null
  designation?: string | null
  department?: { id: string; name: string } | null
  status?: string | null
}

interface BootstrapPayload {
  user: BootstrapUser
  permissions: string[]
  scope: {
    programs: BootstrapProgram[]
    is_global: boolean
  }
  offering_ids: string[]
}

export interface AuthPayload {
  access_token: string
  user: {
    id: string
    email: string
    full_name: string
    first_name: string
    last_name: string
    employee_id: string
    faculty_type: string
    title?: string
    designation?: string
    department: { id: string; name: string } | null
    status: string
  }
  permissions: string[]
  scope: {
    programs: BootstrapProgram[]
    is_global: boolean
  }
  offering_ids: string[]
}

export async function fetchBootstrap(accessToken: string): Promise<BootstrapPayload> {
  const res = await fetch(`${BACKEND}/api/v1/users/me/bootstrap`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error("bootstrap_failed")
  return res.json()
}

export function buildAuthPayload(accessToken: string, bootstrap: BootstrapPayload): AuthPayload {
  const fullName = bootstrap.user.full_name ?? ""
  const spaceIdx = fullName.indexOf(" ")
  const firstName = bootstrap.user.first_name ?? (spaceIdx > 0 ? fullName.slice(0, spaceIdx) : fullName)
  const lastName = bootstrap.user.last_name ?? (spaceIdx > 0 ? fullName.slice(spaceIdx + 1) : "")

  return {
    access_token: accessToken,
    user: {
      id: String(bootstrap.user.id),
      email: bootstrap.user.email,
      full_name: fullName,
      first_name: firstName,
      last_name: lastName,
      employee_id: bootstrap.user.employee_id ?? "",
      faculty_type: bootstrap.user.faculty_type ?? "",
      title: bootstrap.user.title ?? undefined,
      designation: bootstrap.user.designation ?? undefined,
      department: bootstrap.user.department ?? null,
      status: bootstrap.user.status ?? "ACTIVE",
    },
    permissions: bootstrap.permissions ?? [],
    scope: {
      programs: bootstrap.scope?.programs ?? [],
      is_global: bootstrap.scope?.is_global ?? false,
    },
    offering_ids: bootstrap.offering_ids ?? [],
  }
}

export function authJsonResponse(payload: AuthPayload, refreshToken?: string) {
  const res = NextResponse.json(payload)

  if (refreshToken) {
    res.cookies.set("refresh_token", refreshToken, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60,
    })
  }

  res.cookies.set("access_token", payload.access_token, {
    httpOnly: false,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60,
  })

  res.cookies.set("auth-status", "authenticated", {
    httpOnly: false,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 60 * 60,
  })

  return res
}

export function clearAuthResponse(body: Record<string, string>, status = 401) {
  const res = NextResponse.json(body, { status })
  res.cookies.set("refresh_token", "", { maxAge: 0, secure: true, path: "/" })
  res.cookies.set("access_token", "", { maxAge: 0, secure: true, path: "/" })
  res.cookies.set("auth-status", "", { maxAge: 0, secure: true, path: "/" })
  return res
}

export { BACKEND }
