import {
  PublicClientApplication,
  InteractionRequiredAuthError,
  type AccountInfo,
  type AuthenticationResult,
  type RedirectRequest,
  EventType,
} from '@azure/msal-browser'

import {
  entraClientId,
  entraAuthority,
  redirectUri,
  apiScopes,
} from '@/env'

const normalizeScopes = (raw: unknown): string[] => {
  if (!raw) {
    return []
  }

  if (Array.isArray(raw)) {
    return raw.map(String).map((s) => s.trim()).filter(Boolean)
  }

  if (typeof raw === 'string') {
    return raw
      .split(/[ ,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
  }

  return [String(raw)].map((s) => s.trim()).filter(Boolean)
}

const clientId = entraClientId
const authority = entraAuthority
const scopes = normalizeScopes(apiScopes)

const fallbackRedirectUri =
  typeof window !== 'undefined' ? window.location.origin : 'http://localhost'

if (!clientId) {
  // Keep this as a runtime error so misconfiguration is obvious during dev.
  // (Avoid throwing at import-time in tests where env may be missing.)
  console.warn('Entra client ID is not configured (VITE_ENTRA_CLIENT_ID)')
}

export const msalInstance = new PublicClientApplication({
  auth: {
    clientId: clientId ?? 'MISSING_ENTRA_CLIENT_ID',
    authority: authority,
    redirectUri: redirectUri ?? fallbackRedirectUri,
  },
  cache: {
    cacheLocation: 'sessionStorage',
  },
})

let isInitialized = false
let initError: string | null = null

export const getAuthInitState = () => ({
  isInitialized,
  initError,
})

const getDefaultRedirectRequest = (): RedirectRequest => ({
  scopes: scopes.length > 0 ? scopes : undefined,
})

const ensureActiveAccount = (result?: AuthenticationResult | null) => {
  if (result?.account) {
    msalInstance.setActiveAccount(result.account)
    return
  }

  const active = msalInstance.getActiveAccount()
  if (active) {
    return
  }

  const accounts = msalInstance.getAllAccounts()
  if (accounts.length > 0) {
    msalInstance.setActiveAccount(accounts[0])
  }
}

export const initializeMsal = async (): Promise<void> => {
  if (isInitialized) {
    return
  }

  try {
    await msalInstance.initialize()

    // Handle any auth redirect response (if we used redirect flow)
    const result = await msalInstance.handleRedirectPromise()
    ensureActiveAccount(result)

    msalInstance.addEventCallback((event) => {
      if (
        event.eventType === EventType.LOGIN_SUCCESS ||
        event.eventType === EventType.ACQUIRE_TOKEN_SUCCESS
      ) {
        const payload = event.payload as AuthenticationResult | undefined
        ensureActiveAccount(payload)
      }

      if (event.eventType === EventType.LOGOUT_SUCCESS) {
        msalInstance.setActiveAccount(null)
      }
    })

    isInitialized = true
    initError = null
  } catch (err: any) {
    initError = err?.message || 'Failed to initialize MSAL'
    isInitialized = true
    throw err
  }
}

export const login = async (): Promise<void> => {
  await msalInstance.loginRedirect(getDefaultRedirectRequest())
}

export const logout = async (): Promise<void> => {
  const account =
    msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]

  await msalInstance.logoutRedirect({
    account,
  })
}

export const getUser = (): AccountInfo | undefined => {
  return msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]
}

export const getUserRoles = (): string[] => {
  const account = getUser()
  const claims = account?.idTokenClaims as any
  const roles = claims?.roles

  if (Array.isArray(roles)) {
    return roles.map(String)
  }

  if (typeof roles === 'string' && roles.trim()) {
    return [roles.trim()]
  }

  return []
}

const decodeBase64Url = (value: string): string => {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  return atob(padded)
}

export const getRolesFromAccessToken = (accessToken: string): string[] => {
  try {
    const parts = accessToken.split('.')
    if (parts.length < 2) {
      return []
    }

    const payload = JSON.parse(decodeBase64Url(parts[1])) as any
    const roles = payload?.roles

    if (Array.isArray(roles)) {
      return roles.map(String)
    }
    if (typeof roles === 'string' && roles.trim()) {
      return [roles.trim()]
    }

    return []
  } catch {
    return []
  }
}

export const acquireTokenSilentOnly = async (): Promise<string | undefined> => {
  const account = getUser()
  if (!account) {
    return undefined
  }

  const result = await msalInstance.acquireTokenSilent({
    account,
    scopes: scopes.length > 0 ? scopes : undefined,
  })

  return result.accessToken
}

export const acquireToken = async (): Promise<string | undefined> => {
  const account = getUser()
  if (!account) {
    return undefined
  }

  try {
    return await acquireTokenSilentOnly()
  } catch (err: any) {
    if (err instanceof InteractionRequiredAuthError) {
      // If the browser needs user interaction, fall back to redirect.
      await msalInstance.acquireTokenRedirect({
        account,
        scopes: scopes.length > 0 ? scopes : undefined,
      })
      return undefined
    }

    throw err
  }
}
