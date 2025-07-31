import Keycloak from 'keycloak-js'
import { env } from '@/env'
const kcObject = {
  url: env.VITE_KEYCLOAK_URL || 'https://dev.loginproxy.gov.bc.ca/auth',
  realm: env.VITE_KEYCLOAK_REALM || 'standard',
  clientId: env.VITE_KEYCLOAK_CLIENT_ID || 'azure-poc-6086',
}
console.log('Environment variables:', kcObject)

// Setup Keycloak instance as needed
// Pass initialization options as required or leave blank to load from 'keycloak.json'
const _kc = new Keycloak(kcObject)

console.log('Keycloak instance created:', {
  authServerUrl: _kc.authServerUrl,
  realm: _kc.realm,
  clientId: _kc.clientId,
})

export default _kc
