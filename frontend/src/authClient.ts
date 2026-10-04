import Keycloak from 'keycloak-js'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8081',
  realm: import.meta.env.VITE_KEYCLOAK_REALM ?? 'querydesk',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'querydesk-web',
})

export async function initializeAuth(): Promise<void> {
  await keycloak.init({
    onLoad: 'login-required',
    pkceMethod: 'S256',
    checkLoginIframe: false,
  })
}

export async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  if (!keycloak.authenticated) {
    await keycloak.login()
    throw new Error('Redirecting to sign in.')
  }
  await keycloak.updateToken(30)
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${keycloak.token}`)
  return fetch(input, { ...init, headers })
}

export function currentUser() {
  const claims = keycloak.tokenParsed
  return {
    userId: keycloak.subject ?? '',
    email: claims?.email ?? claims?.preferred_username ?? '',
    name: claims?.name ?? claims?.preferred_username ?? claims?.email ?? 'User',
  }
}

export function logout(): void {
  void keycloak.logout({ redirectUri: window.location.origin })
}
