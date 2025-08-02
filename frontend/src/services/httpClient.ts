import axios from 'axios'
import { useAuthStore } from '../stores'

// Create axios instance with authentication
const httpClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
httpClient.interceptors.request.use(
  async (config) => {
    const authStore = useAuthStore.getState()
    if (authStore.isLoggedIn()) {
      // Try to refresh token if it's close to expiring (within 30 seconds)
      try {
        await authStore.updateToken(30)
      } catch (error) {
        console.warn('Token refresh failed in request interceptor:', error)
      }

      const token = authStore.getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// Response interceptor to handle auth errors
httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore.getState()

      // Try to refresh token first before redirecting to login
      try {
        console.log('401 error received, attempting token refresh...')
        const refreshed = await authStore.updateToken(5)

        if (refreshed) {
          console.log('Token refreshed successfully, retrying original request')
          // Retry the original request with the new token
          const originalRequest = error.config
          const newToken = authStore.getToken()
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return httpClient(originalRequest)
          }
        }
      } catch (refreshError) {
        console.error('Token refresh failed on 401 error:', refreshError)
      }

      // If refresh failed or token is still invalid, redirect to login
      console.log('Redirecting to login due to authentication failure')
      authStore.login()
    }
    return Promise.reject(error)
  },
)

export default httpClient
