import _kc from './keycloak'

export const AUTH_TOKEN = '__auth_token'

/**
 * Initializes Keycloak instance and calls the provided callback function if successfully authenticated.
 *
 * @param onAuthenticatedCallback
 */
const initKeycloak = (onAuthenticatedCallback: () => void) => {
  _kc
    .init({
      onLoad: 'login-required',
      checkLoginIframe: false,
    })
    .then((authenticated) => {
      if (!authenticated) {
        console.log('User is not authenticated.')
      } else {
        localStorage.setItem(AUTH_TOKEN, `${_kc.token}`)
      }
      onAuthenticatedCallback()
    })
    .catch(console.error)

  _kc.onTokenExpired = () => {
    _kc.updateToken(3).then((refreshed) => {
      if (refreshed) {
        localStorage.setItem(AUTH_TOKEN, `${_kc.token}`)
      }
    })
  }
}

const doLogin = _kc.login

const doLogout = _kc.logout

const getToken = () => _kc.token

const isLoggedIn = () => !!_kc.token

const updateToken = (
  successCallback:
    | ((value: boolean) => boolean | PromiseLike<boolean>)
    | null
    | undefined,
) => _kc.updateToken(5).then(successCallback).catch(doLogin)

const getUsername = () => _kc.tokenParsed?.display_name

/**
 * Validates that the token's audience claim matches the expected client ID
 * @returns True if audience is valid, false otherwise
 */
const validateAudience = (): boolean => {
  // Get the client ID from the Keycloak instance configuration
  const expectedClientId = _kc.clientId

  if (!expectedClientId) {
    console.error('Keycloak client ID is not configured')
    return false
  }

  if (!_kc.tokenParsed) {
    console.warn('No token parsed available for audience validation')
    return false
  }

  const tokenAudience = _kc.tokenParsed.aud
  if (!tokenAudience) {
    console.warn('Token missing audience claim')
    return false
  }

  // Handle both string and array audience values
  const audiences = Array.isArray(tokenAudience)
    ? tokenAudience
    : [tokenAudience]

  const isValid = audiences.includes(expectedClientId)

  if (!isValid) {
    console.error('Audience validation failed:', {
      expected: expectedClientId,
      received: audiences,
    })
  }

  return isValid
}

/**
 * Determines if a user's role(s) overlap with the role on the private route.  The user's role is determined via jwt.client_roles
 * @param roles
 * @returns True or false, inidicating if the user has the role or not.
 */
const hasRole = (roles: any) => {
  const jwt = _kc.tokenParsed

  // Validate audience claim first
  if (!validateAudience()) {
    console.warn('Audience validation failed, denying role access')
    return false
  }

  const userroles = jwt?.client_roles
  const includesRoles =
    typeof roles === 'string'
      ? userroles?.includes(roles)
      : roles.some((r: any) => userroles?.includes(r))
  return includesRoles
}

const UserService = {
  initKeycloak,
  doLogin,
  doLogout,
  isLoggedIn,
  getToken,
  updateToken,
  getUsername,
  hasRole,
  validateAudience,
}

export default UserService
