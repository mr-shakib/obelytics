import { type NextRequest } from "next/server"
import {
  BACKEND,
  authJsonResponse,
  buildAuthPayload,
  clearAuthResponse,
  fetchBootstrap,
} from "../_shared"

export const runtime = "edge"
export const preferredRegion = "iad1"

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value

  if (!refreshToken) {
    return clearAuthResponse({ error: "no_refresh_token" })
  }

  const refreshRes = await fetch(`${BACKEND}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!refreshRes.ok) {
    return clearAuthResponse({ error: "refresh_failed" })
  }

  const { access_token, refresh_token: newRefreshToken } = await refreshRes.json()

  try {
    const bootstrap = await fetchBootstrap(access_token)
    return authJsonResponse(buildAuthPayload(access_token, bootstrap), newRefreshToken)
  } catch {
    return clearAuthResponse({ error: "bootstrap_failed" }, 502)
  }
}
