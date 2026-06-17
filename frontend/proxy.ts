import { type NextRequest, NextResponse } from "next/server"

const AUTH_ROUTES = ["/login", "/forgot-password", "/reset-password"]
const STUDENT_ROUTES = ["/my-curriculum", "/my-courses", "/my-results", "/my-profile"]
const PUBLIC_PATHS = ["/_next", "/favicon.ico", "/api/auth/"]
const PUBLIC_ROUTES = ["/"]

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next()
  if (PUBLIC_ROUTES.includes(pathname)) return NextResponse.next()

  const authStatus = req.cookies.get("auth-status")?.value
  const isLoggedIn = authStatus === "authenticated"

  const isAuthRoute = AUTH_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "/"))
  const isStudentRoute = STUDENT_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "/"))
  const isDashboardRoute = !isAuthRoute && !isStudentRoute

  if (isLoggedIn && isAuthRoute) {
    return NextResponse.redirect(new URL("/overview", req.url))
  }

  if (!isLoggedIn && (isDashboardRoute || isStudentRoute)) {
    const loginUrl = new URL("/login", req.url)
    loginUrl.searchParams.set("next", pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)" ],
}
