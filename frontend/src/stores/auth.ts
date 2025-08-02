import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import _kc from '../services/keycloak'

export const AUTH_TOKEN = '__auth_token'

interface UserInfo {
  username?: string
  displayName?: string
  email?: string
  roles?: string[]
}

interface AuthState {
  // State
  isInitialized: boolean
  isAuthenticated: boolean
  isLoading: boolean
  token: string | null
  refreshToken: string | null
  userInfo: UserInfo
  error: string | null
  refreshIntervalId: NodeJS.Timeout | null

  // Computed getters
  isLoggedIn: () => boolean
  username: () => string | undefined
  userRoles: () => string[]

  // Actions
  initKeycloak: () => Promise<boolean>
  updateAuthState: () => void
  clearAuthState: () => void
  login: () => Promise<void>
  logout: () => Promise<void>
  updateToken: (minValidity?: number) => Promise<boolean>
  hasRole: (roles: string | string[]) => boolean
  getToken: () => string | null
  checkSSO: () => Promise<boolean>
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  validateAudience: () => boolean
  startTokenRefresh: () => void
  stopTokenRefresh: () => void
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => ({
      // Initial state
      isInitialized: false,
      isAuthenticated: false,
      isLoading: false,
      token: null,
      refreshToken: null,
      userInfo: {},
      error: null,
      refreshIntervalId: null,

      // Computed getters
      isLoggedIn: () => {
        const state = get()
        return (
          state.isAuthenticated && !!state.token && state.validateAudience()
        )
      },

      username: () => {
        const state = get()
        return state.userInfo.displayName || state.userInfo.username
      },

      userRoles: () => {
        const state = get()
        return state.userInfo.roles || []
      },

      // Actions
      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      setError: (error: string | null) => {
        set({ error })
      },

      updateAuthState: () => {
        if (_kc.token) {
          const tokenParsed = _kc.tokenParsed
          set({
            token: _kc.token,
            refreshToken: _kc.refreshToken || null,
            userInfo: tokenParsed
              ? {
                  username: tokenParsed.preferred_username,
                  displayName: tokenParsed.display_name || tokenParsed.name,
                  email: tokenParsed.email,
                  roles: tokenParsed.client_roles || [],
                }
              : {},
          })
          localStorage.setItem(AUTH_TOKEN, _kc.token)
        }
      },

      clearAuthState: () => {
        // Stop token refresh when clearing auth state
        get().stopTokenRefresh()
        set({
          token: null,
          refreshToken: null,
          userInfo: {},
        })
        localStorage.removeItem(AUTH_TOKEN)
      },

      initKeycloak: async (): Promise<boolean> => {
        const state = get()
        if (state.isInitialized) {
          return state.isAuthenticated
        }

        set({ isLoading: true, error: null })

        try {
          // Try different initialization approaches
          const initOptions = {
            onLoad: 'check-sso' as const,
            checkLoginIframe: false,
            enableLogging: true,
            pkceMethod: 'S256',
          }

          const authenticated = await _kc.init(initOptions)

          if (authenticated) {
            get().updateAuthState()
          } else {
            console.log('User is not authenticated, will redirect to login')
            // If not authenticated with check-sso, manually trigger login
            await _kc.login({
              redirectUri: window.location.origin + '/',
            })
            return false // This line won't be reached due to redirect
          }

          set({
            isInitialized: true,
            isAuthenticated: authenticated,
          })

          // Setup token refresh handler for critical failures
          _kc.onTokenExpired = async () => {
            console.log('Token expired, attempting to refresh...')
            try {
              const refreshed = await _kc.updateToken(5)
              if (refreshed) {
                console.log('Token refreshed successfully')
                get().updateAuthState()
              } else {
                console.warn('Token refresh failed')
                await get().logout()
              }
            } catch (error) {
              console.error('Token refresh error:', error)
              await get().logout()
            }
          }

          // Start background token refresh if authenticated
          if (authenticated) {
            get().startTokenRefresh()
          }

          return authenticated
        } catch (err: any) {
          console.error('Failed to initialize Keycloak:', {
            error: err,
            message: err?.message,
            description: err?.error_description,
            stack: err?.stack,
            config: {
              url: _kc.authServerUrl,
              realm: _kc.realm,
              clientId: _kc.clientId,
            },
          })

          set({
            error: err?.message || 'Failed to initialize authentication',
            isInitialized: true,
            isAuthenticated: false,
          })

          return false
        } finally {
          set({ isLoading: false })
        }
      },

      login: async () => {
        set({ isLoading: true, error: null })

        try {
          await _kc.login()
        } catch (err: any) {
          console.error('Login error:', err)
          set({ error: err?.message || 'Login failed' })
        } finally {
          set({ isLoading: false })
        }
      },

      logout: async () => {
        set({ isLoading: true, error: null })

        try {
          get().clearAuthState()
          set({ isAuthenticated: false })
          await _kc.logout()
        } catch (err: any) {
          console.error('Logout error:', err)
          set({ error: err?.message || 'Logout failed' })
        } finally {
          set({ isLoading: false })
        }
      },

      updateToken: async (minValidity = 5): Promise<boolean> => {
        try {
          const refreshed = await _kc.updateToken(minValidity)
          if (refreshed) {
            get().updateAuthState()
          }
          return refreshed
        } catch (err: any) {
          console.error('Token update error:', err)
          await get().logout()
          return false
        }
      },

      hasRole: (roles: string | string[]): boolean => {
        const userRolesList = get().userRoles()
        if (!userRolesList.length) return false

        // Validate audience claim before checking roles
        if (!get().validateAudience()) {
          console.warn('Audience validation failed, denying role access')
          return false
        }

        if (typeof roles === 'string') {
          return userRolesList.includes(roles)
        }

        return roles.some((role) => userRolesList.includes(role))
      },

      validateAudience: (): boolean => {
        // Get the client ID from the Keycloak instance configuration
        const expectedClientId = _kc.clientId

        if (!expectedClientId) {
          console.error('Keycloak client ID is not configured')
          return false
        }

        if (!_kc.tokenParsed) {
          console.warn('No token parsed available for audience validation')
          return false
        }

        const tokenAudience = _kc.tokenParsed.aud
        if (!tokenAudience) {
          console.warn('Token missing audience claim')
          return false
        }

        // Handle both string and array audience values
        const audiences = Array.isArray(tokenAudience)
          ? tokenAudience
          : [tokenAudience]

        const isValid = audiences.includes(expectedClientId)

        if (!isValid) {
          console.error('Audience validation failed:', {
            expected: expectedClientId,
            received: audiences,
          })
        }

        return isValid
      },

      getToken: (): string | null => {
        return get().token
      },

      checkSSO: async (): Promise<boolean> => {
        const state = get()
        if (state.isInitialized) {
          return state.isAuthenticated
        }

        set({ isLoading: true, error: null })

        try {
          const authenticated = await _kc.init({
            onLoad: 'check-sso',
            silentCheckSsoRedirectUri:
              window.location.origin + '/silent-check-sso.html',
            checkLoginIframe: false,
            enableLogging: true,
          })

          if (authenticated) {
            get().updateAuthState()
            set({ isAuthenticated: true })
            // Start background token refresh
            get().startTokenRefresh()
          }

          set({ isInitialized: true })
          return authenticated
        } catch (err: any) {
          console.error('SSO check failed:', err)
          set({
            error: err?.message || 'SSO check failed',
            isInitialized: true,
          })
          return false
        } finally {
          set({ isLoading: false })
        }
      },

      startTokenRefresh: () => {
        // Clear any existing interval
        get().stopTokenRefresh()

        console.log('Starting background token refresh (every 60 seconds)')

        const intervalId = setInterval(async () => {
          const state = get()

          // Only refresh if we're authenticated and have a token
          if (!state.isAuthenticated || !state.token) {
            console.log('Skipping token refresh - not authenticated')
            return
          }

          try {
            console.log('Performing background token refresh...')
            // Refresh token if it expires within 5 minutes (300 seconds)
            const refreshed = await _kc.updateToken(300)

            if (refreshed) {
              console.log('Background token refresh successful')
              get().updateAuthState()
            } else {
              console.log('Token is still valid, no refresh needed')
            }
          } catch (error) {
            console.error('Background token refresh failed:', error)
            // Don't logout on background refresh failure to avoid interrupting user experience
            // The onTokenExpired handler will handle critical failures
          }
        }, 60000) // 60 seconds = 60,000 milliseconds

        set({ refreshIntervalId: intervalId })
      },

      stopTokenRefresh: () => {
        const state = get()
        if (state.refreshIntervalId) {
          console.log('Stopping background token refresh')
          clearInterval(state.refreshIntervalId)
          set({ refreshIntervalId: null })
        }
      },
    }),
    {
      name: 'auth-store',
    },
  ),
)
