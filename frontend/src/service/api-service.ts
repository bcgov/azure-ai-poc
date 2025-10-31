import type { AxiosInstance } from 'axios'
import httpClient from '../services/httpClient'

class APIService {
  private readonly client: AxiosInstance

  constructor() {
    this.client = httpClient
    this.client.interceptors.response.use(
      (config) => {
        console.info(
          `received response status: ${config.status} , data: ${config.data}`,
        )
        return config
      },
      (error) => {
        console.error(error)
        return Promise.reject(error)
      },
    )
  }

  public getAxiosInstance(): AxiosInstance {
    return this.client
  }
}

export default new APIService()
