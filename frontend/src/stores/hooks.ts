import { useEffect } from 'react'
import { useAuthStore } from './auth'

/**
 * Hook to initialize Keycloak authentication on app startup
 */
export const useAuthInit = () => {
  const initKeycloak = useAuthStore((state) => state.initKeycloak)
  const isInitialized = useAuthStore((state) => state.isInitialized)
  const isLoading = useAuthStore((state) => state.isLoading)
  const error = useAuthStore((state) => state.error)
  const stopTokenRefresh = useAuthStore((state) => state.stopTokenRefresh)

  useEffect(() => {
    if (!isInitialized) {
      initKeycloak()
    }

    // Cleanup function to stop token refresh when component unmounts
    return () => {
      stopTokenRefresh()
    }
  }, [initKeycloak, isInitialized, stopTokenRefresh])

  return {
    isInitialized,
    isLoading,
    error,
  }
}

/**
 * Hook to get auth state and actions
 */
export const useAuth = () => {
  const store = useAuthStore()

  return {
    // State
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    error: store.error,
    userInfo: store.userInfo,
    token: store.token,

    // Computed
    isLoggedIn: store.isLoggedIn(),
    username: store.username(),
    userRoles: store.userRoles(),

    // Actions
    login: store.login,
    logout: store.logout,
    updateToken: store.updateToken,
    hasRole: store.hasRole,
    getToken: store.getToken,
    checkSSO: store.checkSSO,
    startTokenRefresh: store.startTokenRefresh,
    stopTokenRefresh: store.stopTokenRefresh,
  }
}
