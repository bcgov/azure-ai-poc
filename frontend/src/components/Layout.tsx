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
        <Header title={'AI Chat'} titleElement="h1">
          <div className="d-flex align-items-center gap-3">
            {isLoggedIn && (
              <div className="d-flex align-items-center gap-3">
                <span className="text-dark fw-semibold">
                  {username || 'User'}
                </span>
                <Button variant="primary" size="sm" onClick={handleLogout}>
                  <i
                    className="bi bi-box-arrow-right"
                    style={{ fontSize: '1rem', marginRight: '0.25rem' }}
                  ></i>
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
