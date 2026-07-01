import { type NextRequest, NextResponse } from "next/server"
import { BACKEND, authJsonResponse, buildAuthPayload, fetchBootstrap } from "../_shared"

export const runtime = "edge"
export const preferredRegion = "iad1"

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

  let payload
  try {
    payload = buildAuthPayload(access_token, await fetchBootstrap(access_token))
  } catch {
    return NextResponse.json({ message: "Failed to load user profile" }, { status: 500 })
  }

  return authJsonResponse(payload, refresh_token)
}
