export const JWT_SECRET =
  process.env.JWT_SECRET ||
  process.env.NEXT_PUBLIC_JWT_SECRET ||
  'IJVQixlsr1I6woFYAN3OOvOAw9rsj1WERC9zcHLRxOt';

/**
 * Decode Base64URL string to Uint8Array bytes
 */
export function base64UrlDecode(str: string): Uint8Array {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
  while (base64.length % 4) {
    base64 += '=';
  }
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Verify JWT signature and expiration using Web Crypto API.
 * Works seamlessly in Edge Runtime, Node.js, and browser environments.
 */
export async function verifyJwt(
  token: string,
  secret: string = JWT_SECRET
): Promise<{ valid: boolean; payload?: any; reason?: string }> {
  try {
    if (!token || typeof token !== 'string') {
      return { valid: false, reason: 'Empty token' };
    }

    const parts = token.split('.');
    if (parts.length !== 3) {
      return { valid: false, reason: 'Invalid token structure' };
    }

    const [headerB64, payloadB64, signatureB64] = parts;
    const encoder = new TextEncoder();

    // 1. Verify HMAC-SHA256 signature
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify']
    );

    const signature = base64UrlDecode(signatureB64) as unknown as BufferSource;
    const data = encoder.encode(`${headerB64}.${payloadB64}`) as unknown as BufferSource;
    const isSignatureValid = await crypto.subtle.verify('HMAC', key, signature, data);

    if (!isSignatureValid) {
      return { valid: false, reason: 'Invalid signature' };
    }

    // 2. Decode payload & verify expiration (set to 1 day)
    const payloadBytes = base64UrlDecode(payloadB64);
    const payloadText = new TextDecoder().decode(payloadBytes);
    const payload = JSON.parse(payloadText);

    if (payload.exp && Date.now() >= payload.exp * 1000) {
      return { valid: false, reason: 'Token expired', payload };
    }

    return { valid: true, payload };
  } catch (err: any) {
    return { valid: false, reason: err?.message || 'Verification exception' };
  }
}

/**
 * Browser-safe check: decodes the JWT and checks expiry only.
 * It does NOT verify the signature, because JWT_SECRET is a server-only env var
 * and is not available in the browser. Real signature verification happens
 * server-side (middleware.ts and the dashboard page.tsx files).
 */
export function decodeJwt(token: string): { valid: boolean; payload?: any; reason?: string } {
  try {
    const parts = token?.split('.');
    if (!parts || parts.length !== 3) return { valid: false, reason: 'Invalid token structure' };
    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(parts[1])));
    if (payload.exp && Date.now() >= payload.exp * 1000) {
      return { valid: false, reason: 'Token expired', payload };
    }
    return { valid: true, payload };
  } catch (err: any) {
    return { valid: false, reason: err?.message || 'Decode failed' };
  }
}

/**
 * Store JWT token in cookie with 1-day (86400s) expiration and localStorage
 */
export function setAuthCookieAndStorage(token: string, user?: any) {
  if (typeof window === 'undefined') return;

  const oneDaySeconds = 86400; // 1 day in seconds
  document.cookie = `token=${token}; Path=/; Max-Age=${oneDaySeconds}; SameSite=Lax`;
  localStorage.setItem('token', token);

  if (user) {
    localStorage.setItem('user', JSON.stringify(user));
  }
}

/**
 * Remove token cookie and localStorage on logout
 */
export function clearAuthCookieAndStorage() {
  if (typeof window === 'undefined') return;

  document.cookie = 'token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT; SameSite=Lax';
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

/**
 * Retrieve token from document.cookie
 */
export function getCookieToken(): string | null {
  if (typeof window === 'undefined') return null;

  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('token='));
  return match ? match.split('=')[1] : null;
}