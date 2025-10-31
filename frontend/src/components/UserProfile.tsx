import React from 'react'
import { useAuth } from '../stores'

/**
 * Example component showing how to use the auth store
 */
const UserProfile: React.FC = () => {
  const {
    isLoggedIn,
    username,
    userInfo,
    userRoles,
    hasRole,
    logout,
    isLoading,
  } = useAuth()

  if (!isLoggedIn) {
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
          <strong>Username:</strong> {username}
        </p>
        <p>
          <strong>Display Name:</strong> {userInfo.displayName}
        </p>
        <p>
          <strong>Email:</strong> {userInfo.email}
        </p>

        {userRoles.length > 0 && (
          <div>
            <strong>Roles:</strong>
            <ul>
              {userRoles.map((role) => (
                <li key={role}>{role}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-3">
          <p>
            <strong>Role Checks:</strong>
          </p>
          <p>Has admin role: {hasRole('admin') ? 'Yes' : 'No'}</p>
          <p>Has user role: {hasRole('user') ? 'Yes' : 'No'}</p>
          <p>
            Has any of [admin, moderator]:{' '}
            {hasRole(['admin', 'moderator']) ? 'Yes' : 'No'}
          </p>
        </div>

        <button className="btn btn-danger mt-3" onClick={() => logout()}>
          Logout
        </button>
      </div>
    </div>
  )
}

export default UserProfile
