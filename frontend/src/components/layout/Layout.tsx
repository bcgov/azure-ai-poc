import React, { type FC } from 'react'
import { Footer, Header } from '@bcgov/design-system-react-components'
import { Button } from 'react-bootstrap'
import { useAuth } from '@/stores'

type Props = {
  children: React.ReactNode
}

const Layout: FC<Props> = ({ children }) => {
  const { isLoggedIn, username, logout } = useAuth()

  const handleLogout = () => {
    logout()
  }

  return (
    <div className="app-layout">
      <div className="app-header shadow-sm">
        <Header title={'AI Chat'} titleElement="h1">
          <div className="d-flex align-items-center gap-3">
            {isLoggedIn && (
              <div className="d-flex align-items-center gap-3">
                <span className="text-dark fw-semibold d-flex align-items-center">
                  <i className="bi bi-person-circle me-2"></i>
                  {username || 'User'}
                </span>
                <Button 
                  variant="primary" 
                  size="sm" 
                  onClick={handleLogout}
                  style={{ borderRadius: '0.5rem', fontWeight: '600' }}
                >
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
      <div className="app-content">{children}</div>
      <div className="app-footer">
        <Footer />
      </div>
    </div>
  )
}

export default Layout
