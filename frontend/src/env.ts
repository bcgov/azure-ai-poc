declare global {
  // eslint-disable-next-line no-unused-vars
  interface Window {
    config: any
  }
}

export const env: Record<string, any> = { ...import.meta.env, ...window.config }

export const entraTenantId: string | undefined = env.VITE_ENTRA_TENANT_ID
export const entraClientId: string | undefined = env.VITE_ENTRA_CLIENT_ID
export const entraAuthority: string | undefined = env.VITE_ENTRA_AUTHORITY

export const apiScopes: string[] | undefined = env.VITE_API_SCOPES
export const redirectUri: string | undefined = env.VITE_REDIRECT_URI
