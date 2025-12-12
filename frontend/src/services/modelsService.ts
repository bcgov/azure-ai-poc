/**
 * Models Service
 *
 * Fetches available AI models from the backend API.
 * This is the single source of truth for model configuration.
 */
import httpClient from './httpClient'

export interface ModelInfo {
  id: string
  deployment: string
  display_name: string
  description: string
  is_default: boolean
}

export interface ModelsResponse {
  models: ModelInfo[]
}

// Cache for models to avoid repeated API calls
let modelsCache: ModelInfo[] | null = null
let modelsCachePromise: Promise<ModelInfo[]> | null = null

/**
 * Fetch available models from the API.
 * Results are cached to avoid repeated API calls.
 */
export async function fetchModels(): Promise<ModelInfo[]> {
  // Return cached models if available
  if (modelsCache) {
    return modelsCache
  }

  // If a request is already in flight, wait for it
  if (modelsCachePromise) {
    return modelsCachePromise
  }

  // Make the request and cache the promise
  modelsCachePromise = httpClient
    .get<ModelsResponse>('/api/v1/models/')
    .then((response) => {
      modelsCache = response.data.models
      return modelsCache
    })
    .finally(() => {
      modelsCachePromise = null
    })

  return modelsCachePromise
}

/**
 * Get the default model ID.
 */
export async function getDefaultModelId(): Promise<string> {
  const models = await fetchModels()
  const defaultModel = models.find((m) => m.is_default)
  return defaultModel?.id || models[0]?.id || 'gpt-4o-mini'
}

/**
 * Clear the models cache to force a refresh on next fetch.
 */
export function clearModelsCache(): void {
  modelsCache = null
}

export default {
  fetchModels,
  getDefaultModelId,
  clearModelsCache,
}
