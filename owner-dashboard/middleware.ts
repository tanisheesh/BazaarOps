import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const authToken = request.cookies.get('auth_token')?.value
  const isAuthPage = request.nextUrl.pathname === '/auth' || request.nextUrl.pathname === '/login'

  // If not logged in and trying to access protected route
  if (!authToken && !isAuthPage) {
    return NextResponse.redirect(new URL('/auth', request.url))
  }

  // If logged in and trying to access auth page
  if (authToken && isAuthPage) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)']
}
