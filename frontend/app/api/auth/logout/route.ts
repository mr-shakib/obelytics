import { type NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export const runtime = "edge"
export const preferredRegion = "iad1"

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value

  // Best-effort: revoke refresh token on backend
  if (refreshToken) {
    await fetch(`${BACKEND}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {})
  }

  const res = NextResponse.json({ ok: true })
  res.cookies.set("refresh_token", "", { maxAge: 0, secure: true, path: "/" })
  res.cookies.set("access_token", "", { maxAge: 0, secure: true, path: "/" })
  res.cookies.set("auth-status", "", { maxAge: 0, secure: true, path: "/" })
  return res
}
