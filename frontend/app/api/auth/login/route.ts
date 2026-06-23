import { type NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function POST(req: NextRequest) {
  const body = await req.json()

  // 1. Login to backend — get access + refresh tokens
  const loginRes = await fetch(`${BACKEND}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!loginRes.ok) {
    const err = await loginRes.json().catch(() => ({ message: "Login failed" }))
    return NextResponse.json(err, { status: loginRes.status })
  }

  const { access_token, refresh_token } = await loginRes.json()

  // 2. Fetch user profile + permissions in parallel
  const [meRes, permsRes] = await Promise.all([
    fetch(`${BACKEND}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${access_token}` },
    }),
    fetch(`${BACKEND}/api/v1/users/me/permissions`, {
      headers: { Authorization: `Bearer ${access_token}` },
    }),
  ])

  if (!meRes.ok || !permsRes.ok) {
    return NextResponse.json({ message: "Failed to load user profile" }, { status: 500 })
  }

  const me = await meRes.json()
  const perms = await permsRes.json()

  // 3. If scoped user, fetch their programs to get names+acronyms
  let programs: { id: string; name: string; acronym: string }[] = []
  const programIds: string[] = (perms.program_ids ?? []).map(String)
  if (!perms.is_super_admin && programIds.length > 0) {
    const progRes = await fetch(`${BACKEND}/api/v1/programs`, {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    if (progRes.ok) {
      const data = await progRes.json()
      const items: Record<string, unknown>[] = Array.isArray(data) ? data : (data.items ?? [])
      programs = items
        .filter((p) => programIds.includes(String(p.id)))
        .map((p) => ({
          id: String(p.id),
          name: String(p.name ?? ""),
          acronym: String(p.code ?? p.acronym ?? ""),
        }))
    }
  }

  // 4. Derive first_name / last_name from full_name
  const fullName: string = me.full_name ?? ""
  const spaceIdx = fullName.indexOf(" ")
  const firstName = spaceIdx > 0 ? fullName.slice(0, spaceIdx) : fullName
  const lastName = spaceIdx > 0 ? fullName.slice(spaceIdx + 1) : ""

  // 5. Build unified response
  const res = NextResponse.json({
    access_token,
    user: {
      id: String(me.id),
      email: me.email,
      full_name: fullName,
      first_name: firstName,
      last_name: lastName,
      faculty_type: me.faculty_type ?? "",
      status: me.status ?? "ACTIVE",
      department: me.department ?? null,
    },
    permissions: perms.permissions ?? [],
    scope: {
      programs,
      is_global: perms.is_super_admin ?? false,
    },
    offering_ids: perms.offering_ids ?? [],
  })

  // 6. Store refresh_token in HttpOnly cookie
  res.cookies.set("refresh_token", refresh_token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 60 * 60,
  })

  return res
}
