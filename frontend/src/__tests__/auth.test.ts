import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const base64UrlEncode = (value: string): string => {
  const b64 = btoa(value)
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

describe('auth-service (Entra/MSAL)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('initializes MSAL and sets active account from redirect result', async () => {
    const mockAccount = { username: 'user@example.com' }

    const initialize = vi.fn().mockResolvedValue(undefined)
    const handleRedirectPromise = vi.fn().mockResolvedValue({ account: mockAccount })
    const setActiveAccount = vi.fn()
    const addEventCallback = vi.fn().mockReturnValue('cb-id')
    const getActiveAccount = vi.fn().mockReturnValue(undefined)
    const getAllAccounts = vi.fn().mockReturnValue([])

    vi.doMock('@azure/msal-browser', () => {
      class InteractionRequiredAuthError extends Error {}
      class PublicClientApplication {
        initialize = initialize
        handleRedirectPromise = handleRedirectPromise
        setActiveAccount = setActiveAccount
        addEventCallback = addEventCallback
        getActiveAccount = getActiveAccount
        getAllAccounts = getAllAccounts
        removeEventCallback = vi.fn()
        loginRedirect = vi.fn()
        logoutRedirect = vi.fn()
        acquireTokenSilent = vi.fn()
        acquireTokenRedirect = vi.fn()
      }

      return {
        PublicClientApplication,
        InteractionRequiredAuthError,
        EventType: {
          LOGIN_SUCCESS: 'LOGIN_SUCCESS',
          ACQUIRE_TOKEN_SUCCESS: 'ACQUIRE_TOKEN_SUCCESS',
          LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
        },
      }
    })

    vi.doMock('@/env', () => ({
      entraClientId: 'client-id',
      entraAuthority: 'https://login.microsoftonline.com/tenant',
      redirectUri: 'http://localhost:5173',
      apiScopes: 'scope-one scope-two',
    }))

    const mod = await import('@/service/auth-service')

    await mod.initializeMsal()

    expect(initialize).toHaveBeenCalledTimes(1)
    expect(handleRedirectPromise).toHaveBeenCalledTimes(1)
    expect(setActiveAccount).toHaveBeenCalledWith(mockAccount)
    expect(addEventCallback).toHaveBeenCalledTimes(1)
  })

  it('login calls msal loginRedirect with normalized scopes', async () => {
    const loginRedirect = vi.fn().mockResolvedValue(undefined)

    vi.doMock('@azure/msal-browser', () => {
      class InteractionRequiredAuthError extends Error {}
      class PublicClientApplication {
        initialize = vi.fn().mockResolvedValue(undefined)
        handleRedirectPromise = vi.fn().mockResolvedValue(null)
        setActiveAccount = vi.fn()
        addEventCallback = vi.fn()
        getActiveAccount = vi.fn().mockReturnValue(undefined)
        getAllAccounts = vi.fn().mockReturnValue([])
        removeEventCallback = vi.fn()
        loginRedirect = loginRedirect
        logoutRedirect = vi.fn()
        acquireTokenSilent = vi.fn()
        acquireTokenRedirect = vi.fn()
      }

      return {
        PublicClientApplication,
        InteractionRequiredAuthError,
        EventType: {
          LOGIN_SUCCESS: 'LOGIN_SUCCESS',
          ACQUIRE_TOKEN_SUCCESS: 'ACQUIRE_TOKEN_SUCCESS',
          LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
        },
      }
    })

    vi.doMock('@/env', () => ({
      entraClientId: 'client-id',
      entraAuthority: 'https://login.microsoftonline.com/tenant',
      redirectUri: 'http://localhost:5173',
      apiScopes: 'scope-one,scope-two',
    }))

    const mod = await import('@/service/auth-service')

    await mod.login()

    expect(loginRedirect).toHaveBeenCalledTimes(1)
    expect(loginRedirect).toHaveBeenCalledWith({ scopes: ['scope-one', 'scope-two'] })
  })

  it('logout uses active account when available', async () => {
    const logoutRedirect = vi.fn().mockResolvedValue(undefined)
    const active = { username: 'active@example.com' }

    vi.doMock('@azure/msal-browser', () => {
      class InteractionRequiredAuthError extends Error {}
      class PublicClientApplication {
        initialize = vi.fn().mockResolvedValue(undefined)
        handleRedirectPromise = vi.fn().mockResolvedValue(null)
        setActiveAccount = vi.fn()
        addEventCallback = vi.fn()
        getActiveAccount = vi.fn().mockReturnValue(active)
        getAllAccounts = vi.fn().mockReturnValue([])
        removeEventCallback = vi.fn()
        loginRedirect = vi.fn()
        logoutRedirect = logoutRedirect
        acquireTokenSilent = vi.fn()
        acquireTokenRedirect = vi.fn()
      }

      return {
        PublicClientApplication,
        InteractionRequiredAuthError,
        EventType: {
          LOGIN_SUCCESS: 'LOGIN_SUCCESS',
          ACQUIRE_TOKEN_SUCCESS: 'ACQUIRE_TOKEN_SUCCESS',
          LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
        },
      }
    })

    vi.doMock('@/env', () => ({
      entraClientId: 'client-id',
      entraAuthority: 'https://login.microsoftonline.com/tenant',
      redirectUri: 'http://localhost:5173',
      apiScopes: undefined,
    }))

    const mod = await import('@/service/auth-service')

    await mod.logout()

    expect(logoutRedirect).toHaveBeenCalledTimes(1)
    expect(logoutRedirect).toHaveBeenCalledWith({ account: active })
  })

  it('acquireToken returns access token from silent flow', async () => {
    const account = { username: 'active@example.com' }
    const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: 'token-123' })

    vi.doMock('@azure/msal-browser', () => {
      class InteractionRequiredAuthError extends Error {}
      class PublicClientApplication {
        initialize = vi.fn().mockResolvedValue(undefined)
        handleRedirectPromise = vi.fn().mockResolvedValue(null)
        setActiveAccount = vi.fn()
        addEventCallback = vi.fn()
        getActiveAccount = vi.fn().mockReturnValue(account)
        getAllAccounts = vi.fn().mockReturnValue([])
        removeEventCallback = vi.fn()
        loginRedirect = vi.fn()
        logoutRedirect = vi.fn()
        acquireTokenSilent = acquireTokenSilent
        acquireTokenRedirect = vi.fn()
      }

      return {
        PublicClientApplication,
        InteractionRequiredAuthError,
        EventType: {
          LOGIN_SUCCESS: 'LOGIN_SUCCESS',
          ACQUIRE_TOKEN_SUCCESS: 'ACQUIRE_TOKEN_SUCCESS',
          LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
        },
      }
    })

    vi.doMock('@/env', () => ({
      entraClientId: 'client-id',
      entraAuthority: 'https://login.microsoftonline.com/tenant',
      redirectUri: 'http://localhost:5173',
      apiScopes: 'scope-one',
    }))

    const mod = await import('@/service/auth-service')

    const token = await mod.acquireToken()

    expect(token).toBe('token-123')
    expect(acquireTokenSilent).toHaveBeenCalledTimes(1)
  })

  it('acquireToken falls back to redirect when interaction is required', async () => {
    const account = { username: 'active@example.com' }

    vi.doMock('@azure/msal-browser', () => {
      class InteractionRequiredAuthError extends Error {}
      const acquireTokenSilent = vi
        .fn()
        .mockRejectedValue(new InteractionRequiredAuthError('interaction required'))
      const acquireTokenRedirect = vi.fn().mockResolvedValue(undefined)

      class PublicClientApplication {
        initialize = vi.fn().mockResolvedValue(undefined)
        handleRedirectPromise = vi.fn().mockResolvedValue(null)
        setActiveAccount = vi.fn()
        addEventCallback = vi.fn()
        getActiveAccount = vi.fn().mockReturnValue(account)
        getAllAccounts = vi.fn().mockReturnValue([])
        removeEventCallback = vi.fn()
        loginRedirect = vi.fn()
        logoutRedirect = vi.fn()
        acquireTokenSilent = acquireTokenSilent
        acquireTokenRedirect = acquireTokenRedirect
      }

      return {
        PublicClientApplication,
        InteractionRequiredAuthError,
        EventType: {
          LOGIN_SUCCESS: 'LOGIN_SUCCESS',
          ACQUIRE_TOKEN_SUCCESS: 'ACQUIRE_TOKEN_SUCCESS',
          LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
        },
      }
    })

    vi.doMock('@/env', () => ({
      entraClientId: 'client-id',
      entraAuthority: 'https://login.microsoftonline.com/tenant',
      redirectUri: 'http://localhost:5173',
      apiScopes: 'scope-one',
    }))

    const mod = await import('@/service/auth-service')

    const token = await mod.acquireToken()

    expect(token).toBeUndefined()
    expect((mod as any).msalInstance.acquireTokenRedirect).toHaveBeenCalledTimes(1)
  })

  it('extracts roles from access token JWT payload', async () => {
    vi.doMock('@azure/msal-browser', () => {
      class InteractionRequiredAuthError extends Error {}
      class PublicClientApplication {
        initialize = vi.fn().mockResolvedValue(undefined)
        handleRedirectPromise = vi.fn().mockResolvedValue(null)
        setActiveAccount = vi.fn()
        addEventCallback = vi.fn()
        getActiveAccount = vi.fn().mockReturnValue(undefined)
        getAllAccounts = vi.fn().mockReturnValue([])
        removeEventCallback = vi.fn()
        loginRedirect = vi.fn()
        logoutRedirect = vi.fn()
        acquireTokenSilent = vi.fn()
        acquireTokenRedirect = vi.fn()
      }

      return {
        PublicClientApplication,
        InteractionRequiredAuthError,
        EventType: {
          LOGIN_SUCCESS: 'LOGIN_SUCCESS',
          ACQUIRE_TOKEN_SUCCESS: 'ACQUIRE_TOKEN_SUCCESS',
          LOGOUT_SUCCESS: 'LOGOUT_SUCCESS',
        },
      }
    })

    vi.doMock('@/env', () => ({
      entraClientId: 'client-id',
      entraAuthority: 'https://login.microsoftonline.com/tenant',
      redirectUri: 'http://localhost:5173',
      apiScopes: undefined,
    }))

    const mod = await import('@/service/auth-service')

    const payload = base64UrlEncode(JSON.stringify({ roles: ['r1', 'r2'] }))
    const token = `header.${payload}.sig`

    expect(mod.getRolesFromAccessToken(token)).toEqual(['r1', 'r2'])
  })
})

describe('api-client (token injection + 401 retry)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  it('injects bearer token on requests when available', async () => {
    const acquireToken = vi.fn().mockResolvedValue('access-token')

    vi.doMock('@/service/auth-service', () => ({
      acquireToken,
      login: vi.fn(),
    }))

    const { apiClient } = await import('@/service/api-client')

    const requestHandler = (apiClient.interceptors.request as any).handlers[0]
      .fulfilled

    const config = await requestHandler({ headers: {} })

    expect(acquireToken).toHaveBeenCalledTimes(1)
    expect(config.headers.Authorization).toBe('Bearer access-token')
  })

  it('retries once on 401 with refreshed token and sets retry flag', async () => {
    const acquireToken = vi.fn().mockResolvedValue('fresh-token')
    const login = vi.fn()

    vi.doMock('@/service/auth-service', () => ({
      acquireToken,
      login,
    }))

    const { apiClient } = await import('@/service/api-client')

    const requestSpy = vi.spyOn(apiClient, 'request').mockResolvedValue({} as any)

    const rejected = (apiClient.interceptors.response as any).handlers[0]
      .rejected

    const originalRequest: any = { url: '/x', method: 'get', headers: {} }
    await rejected({ response: { status: 401 }, config: originalRequest })
      .catch(() => undefined)

    expect(originalRequest.__entraRetry).toBe(true)
    expect(originalRequest.headers.Authorization).toBe('Bearer fresh-token')
    expect(requestSpy).toHaveBeenCalledWith(originalRequest)
    expect(login).not.toHaveBeenCalled()
  })

  it('does not infinite-retry: second 401 triggers login', async () => {
    const acquireToken = vi.fn().mockResolvedValue('fresh-token')
    const login = vi.fn()

    vi.doMock('@/service/auth-service', () => ({
      acquireToken,
      login,
    }))

    const { apiClient } = await import('@/service/api-client')

    const requestSpy = vi.spyOn(apiClient, 'request').mockResolvedValue({} as any)

    const rejected = (apiClient.interceptors.response as any).handlers[0]
      .rejected

    const originalRequest: any = { url: '/x', method: 'get', headers: {}, __entraRetry: true }
    await rejected({ response: { status: 401 }, config: originalRequest })
      .catch(() => undefined)

    expect(login).toHaveBeenCalledTimes(1)
    expect(requestSpy).not.toHaveBeenCalled()
  })
})
