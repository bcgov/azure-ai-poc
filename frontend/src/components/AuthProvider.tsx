import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { MsalProvider } from '@azure/msal-react'

import {
  msalInstance,
  initializeMsal,
  getAuthInitState,
  getUser,
  getUserRoles,
  acquireTokenSilentOnly,
  getRolesFromAccessToken,
  login,
  logout,
} from '@/service/auth-service'

type AuthContextValue = {
  isInitialized: boolean
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean
  user: {
    name?: string
    username?: string
  } | null
  roles: string[]
  login: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [roles, setRoles] = useState<string[]>([])
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let mounted = true

    const run = async () => {
      try {
        setIsLoading(true)
        await initializeMsal()

        if (!mounted) {
          return
        }

        const state = getAuthInitState()
        setIsInitialized(state.isInitialized)
        setError(state.initError)

        const idTokenRoles = getUserRoles()
        setRoles(idTokenRoles)

        // Prefer access-token roles if we can acquire silently.
        const accessToken = await acquireTokenSilentOnly().catch(() => undefined)
        if (accessToken) {
          const accessTokenRoles = getRolesFromAccessToken(accessToken)
          if (accessTokenRoles.length > 0) {
            setRoles(accessTokenRoles)
          }
        }
      } catch (err: any) {
        if (!mounted) {
          return
        }

        setIsInitialized(true)
        setError(err?.message || 'Failed to initialize authentication')
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }

    run()

    const cb = msalInstance.addEventCallback(() => {
      // Force a refresh of derived data (account/roles) on login/logout.
      setTick((x) => x + 1)
    })

    return () => {
      mounted = false
      if (cb) {
        msalInstance.removeEventCallback(cb)
      }
    }
  }, [])

  const value = useMemo<AuthContextValue>(() => {
    const account = getUser()

    return {
      isInitialized,
      isLoading,
      error,
      isAuthenticated: Boolean(account),
      user: account
        ? {
            name: account.name,
            username: account.username,
          }
        : null,
      roles,
      login,
      logout,
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isInitialized, isLoading, error, roles, tick])

  return (
    <MsalProvider instance={msalInstance}>
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    </MsalProvider>
  )
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}

export const useIsAuthenticated = (): boolean => {
  return useAuth().isAuthenticated
}

export const useUserRoles = (): string[] => {
  return useAuth().roles
}
