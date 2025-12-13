import React from 'react'

import { useAuth } from '@/components/AuthProvider'

const LoginButton = () => {
  const { isAuthenticated, user, roles, login, logout, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  if (!isAuthenticated) {
    return (
      <button
        type="button"
        className="btn btn-primary btn-sm"
        aria-label="Sign in with Microsoft Entra ID"
        onClick={() => login()}
      >
        Login
      </button>
    )
  }

  return (
    <div className="d-flex align-items-center gap-2">
      <span className="text-dark fw-semibold">
        {user?.name || user?.username || 'User'}
      </span>
      {roles.length > 0 && (
        <span className="text-muted small">Roles: {roles.join(', ')}</span>
      )}
      <button
        type="button"
        className="btn btn-primary btn-sm"
        aria-label="Sign out"
        onClick={() => logout()}
      >
        Logout
      </button>
    </div>
  )
}

export default LoginButton
