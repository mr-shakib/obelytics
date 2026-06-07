import { type NextRequest, NextResponse } from "next/server"

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value

  if (!refreshToken) {
    return NextResponse.json({ error: "no_refresh_token" }, { status: 401 })
  }

  // Backend expects refresh_token in the JSON body, not as a cookie
  const backendRes = await fetch(`${BACKEND}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!backendRes.ok) {
    const res = NextResponse.json({ error: "refresh_failed" }, { status: 401 })
    res.cookies.set("refresh_token", "", { maxAge: 0, path: "/" })
    res.cookies.set("auth-status", "", { maxAge: 0, path: "/" })
    return res
  }

  const { access_token, refresh_token: newRefreshToken } = await backendRes.json()

  const res = NextResponse.json({ access_token })

  // Rotate the refresh token cookie
  res.cookies.set("refresh_token", newRefreshToken, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 60 * 60,
  })

  return res
}
