import React, { type FC } from 'react'
import { Footer, Header } from '@bcgov/design-system-react-components'
import { Link } from '@tanstack/react-router'
import { Button } from 'react-bootstrap'
import UserService from '../services/user-service'

type Props = {
  children: React.ReactNode
}

const Layout: FC<Props> = ({ children }) => {
  const handleLogout = () => {
    UserService.doLogout()
  }

  return (
    <div className="d-flex flex-column min-vh-100">
      <div className="mb-3">
        <Header title={'QuickStart Azure Containers Using App Service'}>
          <div className="d-flex align-items-center gap-3">
            <Link to="/">
              <Button variant="light" size="lg">
                <i className="bi bi-house-door-fill" />
              </Button>
            </Link>
            {UserService.isLoggedIn() && (
              <div className="d-flex align-items-center gap-3">
                <span className="text-white">
                  Welcome, {UserService.getUsername() || 'User'}
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
      <div className="d-flex flex-grow-1 align-items-start justify-content-center mt-5 mb-5 ml-1 mr-1">
        {children}
      </div>
      <Footer />
    </div>
  )
}

export default Layout
