import React, { type FC } from 'react'
import { Footer, Header } from '@bcgov/design-system-react-components'
import { Link } from '@tanstack/react-router'
import { Button } from 'react-bootstrap'
import { useAuth } from '../stores'

type Props = {
  children: React.ReactNode
}

const Layout: FC<Props> = ({ children }) => {
  const { isLoggedIn, username, logout } = useAuth()

  const handleLogout = () => {
    logout()
  }

  return (
    <div className="d-flex flex-column min-vh-100">
      <div className="mb-3">
        <Header title={'AI Chat'}>
          <div className="d-flex align-items-center gap-3">
            <Link to="/">
              <Button variant="light" size="lg">
                <i className="bi bi-house-door-fill" />
              </Button>
            </Link>
            {isLoggedIn && (
              <div className="d-flex align-items-center gap-3">
                <span className="text-white">
                  Welcome, {username || 'User'}
                </span>
                <Button
                  variant="outline-light"
                  size="sm"
                  onClick={handleLogout}
                >
                  Sign Out
                </Button>
              </div>
            )}
          </div>
        </Header>
      </div>
      <div className="flex-grow-1 d-flex flex-column">{children}</div>
      <Footer />
    </div>
  )
}

export default Layout
