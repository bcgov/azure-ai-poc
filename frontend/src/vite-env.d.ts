/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_KEYCLOAK_URL: string
  readonly VITE_KEYCLOAK_REALM: string
  readonly VITE_KEYCLOAK_CLIENT_ID: string
  readonly VITE_API_BASE_URL: string

  readonly VITE_ENTRA_TENANT_ID?: string
  readonly VITE_ENTRA_CLIENT_ID?: string
  readonly VITE_ENTRA_AUTHORITY?: string
  readonly VITE_API_SCOPES?: string
  readonly VITE_REDIRECT_URI?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
