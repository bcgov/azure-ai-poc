import React, { type FC, useEffect, useRef } from 'react'
import { useAuth } from '@/components/AuthProvider'

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
  const { isInitialized, isLoading, error, isAuthenticated, roles, login } =
    useAuth()
  
  // Prevent multiple login attempts
  const loginAttemptedRef = useRef(false)

  // Auto-redirect to Entra login if not authenticated
  useEffect(() => {
    if (isInitialized && !isLoading && !isAuthenticated && !error && !loginAttemptedRef.current) {
      loginAttemptedRef.current = true
      login()
    }
  }, [isInitialized, isLoading, isAuthenticated, error, login])

  // Show loading state while initializing or redirecting to login
  if (!isInitialized || isLoading || (!isAuthenticated && !error)) {
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

  // Check role-based access if required
  if (requiredRoles) {
    const required = Array.isArray(requiredRoles)
      ? requiredRoles
      : [requiredRoles]

    const hasAllRequired = required.every((role) => roles.includes(role))
    if (!hasAllRequired) {
      return (
        <div className="alert alert-warning" role="alert">
          <h4 className="alert-heading">Access Denied</h4>
          <p>You don't have the required permissions to access this page.</p>
        </div>
      )
    }
  }

  // All checks passed, render children
  return <>{children}</>
}

export default AuthGuard
