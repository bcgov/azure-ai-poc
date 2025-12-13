import axios from 'axios'

import { acquireToken, login } from '@/service/auth-service'

export const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  async (config) => {
    // In SSR/tests, avoid touching browser auth state.
    if (typeof window === 'undefined') {
      return config
    }

    const token = await acquireToken().catch((err) => {
      console.warn('Failed to acquire token for API request', err)
      return undefined
    })

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => Promise.reject(error),
)

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status

    if (status === 401 && typeof window !== 'undefined') {
      const originalRequest = error?.config as any

      // Prevent infinite retry loops if the retried request also returns 401.
      if (originalRequest?.__entraRetry) {
        login()
      } else {
        if (originalRequest) {
          originalRequest.__entraRetry = true
        }

        // Retry once with a fresh token; if it still fails, trigger login.
        try {
          const token = await acquireToken()

          if (token && originalRequest) {
            originalRequest.headers = originalRequest.headers ?? {}
            originalRequest.headers.Authorization = `Bearer ${token}`
            return apiClient.request(originalRequest)
          }
        } catch (refreshError) {
          console.warn('Token refresh failed after 401', refreshError)
        }

        login()
      }
    }

    // Log API errors with structured format
    console.error('API error', {
      status,
      url: error?.config?.url,
      method: error?.config?.method,
      detail: error?.response?.data,
    })

    return Promise.reject(error)
  },
)

