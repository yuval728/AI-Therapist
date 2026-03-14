import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get("access_token")?.value

  // Public routes that don't require authentication
  const publicRoutes = ["/auth"]
  const isPublicRoute = publicRoutes.includes(pathname)

  // Root route handling
  if (pathname === "/") {
    if (token) {
      return NextResponse.redirect(new URL("/chat", request.url))
    } else {
      return NextResponse.redirect(new URL("/auth", request.url))
    }
  }

  // Protected routes
  const protectedRoutes = ["/chat"]
  const isProtectedRoute = protectedRoutes.some((route) => pathname.startsWith(route))

  if (isProtectedRoute && !token) {
    // Redirect to auth if trying to access protected route without token
    const response = NextResponse.redirect(new URL("/auth", request.url))
    response.cookies.delete("access_token")
    return response
  }

  if (isPublicRoute && token) {
    // Redirect to chat if trying to access auth page while authenticated
    return NextResponse.redirect(new URL("/chat", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
}
