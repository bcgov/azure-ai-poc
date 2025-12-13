import React, { type FC } from 'react'
import { Footer, Header } from '@bcgov/design-system-react-components'
import { Button } from 'react-bootstrap'
import LoginButton from '@/components/LoginButton'
import { useNavigate, useLocation } from '@tanstack/react-router'
import '@/styles/chat.css'

type Props = {
  children: React.ReactNode
}

const Layout: FC<Props> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()

  const isOnChat = location.pathname === '/' || location.pathname === '/chat'
  const isOnOrchestrator = location.pathname === '/bc-data-query'

  return (
    <div className="app-layout">
      <div className="app-header shadow-sm">
        <Header title={'AI POC'} titleElement="h1">
          <div className="d-flex align-items-center gap-3">
            {/* AI Chat Button in Header */}
            <Button
              variant={isOnChat ? 'primary' : 'outline-primary'}
              size="sm"
              onClick={() => navigate({ to: '/' })}
              style={{ 
                borderRadius: '1.5rem', 
                fontWeight: '600',
                padding: '0.375rem 1rem',
                backgroundColor: isOnChat ? '#003366' : undefined,
                borderColor: '#003366',
                color: isOnChat ? 'white' : '#003366'
              }}
            >
              <i className="bi bi-chat-dots me-1"></i>
              AI Chat
            </Button>
            
            {/* BC Data Query Button in Header */}
            <Button
              variant={isOnOrchestrator ? 'primary' : 'outline-primary'}
              size="sm"
              onClick={() => navigate({ to: '/bc-data-query' })}
              style={{ 
                borderRadius: '1.5rem', 
                fontWeight: '600',
                padding: '0.375rem 1rem',
                backgroundColor: isOnOrchestrator ? '#003366' : undefined,
                borderColor: '#003366',
                color: isOnOrchestrator ? 'white' : '#003366'
              }}
            >
              <i className="bi bi-diagram-3 me-1"></i>
              BC Data Query
            </Button>
            
            <LoginButton />
          </div>
        </Header>
      </div>
      <div className="app-content">{children}</div>
      {!isOnChat && !isOnOrchestrator && (
        <div className="app-footer-wrapper">
          <Footer />
        </div>
      )}
    </div>
  )
}

export default Layout
