import React, { useEffect } from 'react'

import { useAuth } from '@/components/AuthProvider'

type Props = {
  children: React.ReactNode
  fallback?: React.ReactNode
}

const ProtectedRoute = ({ children, fallback = <div>Loading...</div> }: Props) => {
  const { isInitialized, isLoading, error, isAuthenticated, login } = useAuth()

  useEffect(() => {
    if (isInitialized && !isLoading && !error && !isAuthenticated) {
      // Trigger login as soon as we know we aren't authenticated.
      login()
    }
  }, [error, isAuthenticated, isInitialized, isLoading, login])

  if (!isInitialized || isLoading) {
    return <>{fallback}</>
  }

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

  if (!isAuthenticated) {
    return (
      <div className="text-center">
        <h3>Authentication Required</h3>
        <p>Redirecting to login...</p>
      </div>
    )
  }

  return <>{children}</>
}

export default ProtectedRoute
