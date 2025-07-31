import Keycloak from 'keycloak-js'

// Setup Keycloak instance as needed
// Pass initialization options as required or leave blank to load from 'keycloak.json'
const _kc = new Keycloak({
  url:
    import.meta.env.VITE_KEYCLOAK_URL ||
    'https://dev.loginproxy.gov.bc.ca/auth',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'standard',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'nr-arch-data-in-5757',
})

export default _kc
