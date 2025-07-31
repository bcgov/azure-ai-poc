import axios from 'axios'
import UserService from './user-service'

// Create axios instance with authentication
const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
httpClient.interceptors.request.use(
  async (config) => {
    if (UserService.isLoggedIn()) {
      const token = UserService.getToken()
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
  (error) => {
    if (error.response?.status === 401) {
      UserService.doLogin()
    }
    return Promise.reject(error)
  },
)

export default httpClient
