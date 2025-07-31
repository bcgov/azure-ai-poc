import React, { type FC } from 'react'
import { useAuth, useAuthInit } from '../stores'

type Props = {
  children: React.ReactNode
  requiredRoles?: string | string[]
  fallback?: React.ReactNode
}

const AuthGuard: FC<Props> = ({
  children,
  requiredRoles,
  fallback = <div>Loading...</div>,
}) => {
  const { isInitialized, isLoading, error } = useAuthInit()
  const { isLoggedIn, hasRole, login } = useAuth()

  // Show loading state while initializing
  if (!isInitialized || isLoading) {
    return <>{fallback}</>
  }

  // Show error state if initialization failed
  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        <h4 className="alert-heading">Authentication Error</h4>
        <p>Failed to initialize authentication: {error}</p>
        <button
          className="btn btn-primary"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    )
  }

  // If not logged in, show login prompt
  if (!isLoggedIn) {
    return (
      <div className="text-center">
        <h3>Authentication Required</h3>
        <p>Please log in to access this application.</p>
        <button className="btn btn-primary" onClick={() => login()}>
          Log In
        </button>
      </div>
    )
  }

  // Check role-based access if required
  if (requiredRoles && !hasRole(requiredRoles)) {
    return (
      <div className="alert alert-warning" role="alert">
        <h4 className="alert-heading">Access Denied</h4>
        <p>You don't have the required permissions to access this page.</p>
      </div>
    )
  }

  // All checks passed, render children
  return <>{children}</>
}

export default AuthGuard
