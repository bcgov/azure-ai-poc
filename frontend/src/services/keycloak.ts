import Keycloak from 'keycloak-js'

const kcObject = {
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
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
