export type SessionUser = {
  user_id: string
  email: string
  preferred_username: string
}

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'querydesk-session-token'
const USER_KEY = 'querydesk-session-user'
let activeUser: SessionUser | null = null

function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  activeUser = null
}

export async function initializeAuth(): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return
  try {
    const response = await fetch(`${API}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      clearSession()
      return
    }
    activeUser = await response.json() as SessionUser
    localStorage.setItem(USER_KEY, JSON.stringify(activeUser))
  } catch {
    // The API may be temporarily unavailable. Require a fresh sign-in on reload.
    clearSession()
  }
}

export async function login(email: string): Promise<SessionUser> {
  const response = await fetch(`${API}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  const data = await response.json().catch(() => ({})) as {
    access_token?: string
    user?: SessionUser
    detail?: string
  }
  if (!response.ok || !data.access_token || !data.user) {
    throw new Error(data.detail ?? `Could not sign in (HTTP ${response.status}).`)
  }
  activeUser = data.user
  localStorage.setItem(TOKEN_KEY, data.access_token)
  localStorage.setItem(USER_KEY, JSON.stringify(data.user))
  return data.user
}

export async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) throw new Error('Enter your email to sign in.')
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(input, { ...init, headers })
  if (response.status === 401) {
    clearSession()
    window.dispatchEvent(new Event('querydesk-session-expired'))
  }
  return response
}

export function currentUser(): SessionUser | null {
  if (activeUser) return activeUser
  const saved = localStorage.getItem(USER_KEY)
  if (!saved) return null
  try {
    activeUser = JSON.parse(saved) as SessionUser
    return activeUser
  } catch {
    clearSession()
    return null
  }
}

export async function logout(): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY)
  try {
    if (token) {
      await fetch(`${API}/api/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
    }
  } finally {
    clearSession()
  }
}
