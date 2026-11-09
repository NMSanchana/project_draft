import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { verifyJwt, JWT_SECRET } from './lib/auth';

// Protected path prefixes that require valid JWT
const PROTECTED_PREFIXES = [
  '/en/dashboard',
  '/dashboard',
  '/en/insights',
  '/insights',
  '/en/reports',
  '/reports',
  '/en/documents',
  '/documents',
  '/en/settings',
  '/settings',
];

// Auth pages (login/register)
const AUTH_PAGES = ['/en/login', '/login'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Ignore static assets, next internal files, and favicon
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/images') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.startsWith('/api')
  ) {
    return NextResponse.next();
  }

  // Retrieve token from request cookies
  const token = request.cookies.get('token')?.value;

  // Check if current path is a protected route
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  // Check if current path is an auth page (login)
  const isAuthPage = AUTH_PAGES.some(
    (page) => pathname === page || pathname.startsWith(`${page}/`)
  );

  // 1. Verify token if present
  let isAuthenticated = false;
  if (token) {
    const { valid } = await verifyJwt(token, JWT_SECRET);
    isAuthenticated = valid;
  }

  // 2. Protected Route Guard: If not authenticated, redirect to landing home page
  if (isProtected) {
    if (!isAuthenticated) {
      const redirectUrl = new URL('/en/landing', request.url);
      const response = NextResponse.redirect(redirectUrl);
      if (token) {
        // Clear invalid or expired token cookie
        response.cookies.delete('token');
      }
      return response;
    }
    return NextResponse.next();
  }

  // 3. Auth Page Guard: If already authenticated and visiting /login, send to dashboard
  if (isAuthPage && isAuthenticated) {
    return NextResponse.redirect(new URL('/en/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images (public images)
     */
    '/((?!_next/static|_next/image|favicon.ico|images).*)',
  ],
};
