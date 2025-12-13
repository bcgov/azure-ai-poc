import React from 'react'
import { useAuth } from '@/components/AuthProvider'

/**
 * Example component showing how to use the auth store
 */
const UserProfile: React.FC = () => {
  const { isAuthenticated, user, roles, logout, isLoading } = useAuth()

  if (!isAuthenticated) {
    return <div>Please log in to view your profile.</div>
  }

  if (isLoading) {
    return <div>Loading profile...</div>
  }

  return (
    <div className="card">
      <div className="card-header">
        <h5>User Profile</h5>
      </div>
      <div className="card-body">
        <p>
          <strong>Username:</strong> {user?.username}
        </p>
        <p>
          <strong>Display Name:</strong> {user?.name}
        </p>
        <p>
          <strong>Email:</strong> {user?.username}
        </p>

        {roles.length > 0 && (
          <div>
            <strong>Roles:</strong>
            <ul>
              {roles.map((role) => (
                <li key={role}>{role}</li>
              ))}
            </ul>
          </div>
        )}

        <button className="btn btn-danger mt-3" onClick={() => logout()}>
          Logout
        </button>
      </div>
    </div>
  )
}

export default UserProfile
