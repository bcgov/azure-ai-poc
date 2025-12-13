import { EmptyState } from '@/components/common'
import { useAuth } from '@/components/AuthProvider'
import type { FC } from 'react'
import { useState } from 'react'
import { Button, Col, Container, Row } from 'react-bootstrap'
import ChatPage from '@/pages/ChatPage'
import TenantManagementPage from '@/pages/TenantManagementPage'

const Dashboard: FC = () => {
  const [activeView, setActiveView] = useState<'chat' | 'tenants'>('chat')
  const { roles } = useAuth()

  const canManageTenants = roles.includes('TENANT_ADMIN')

  return (
    <Container fluid className="p-0">
      {/* Only show tenant tab if user has admin role */}
      {canManageTenants && (
        <Row className="g-0">
          <Col xs={12}>
            <div className="d-flex justify-content-center py-2 border-bottom bg-light">
              <div className="d-flex gap-2">
                <Button
                  variant={activeView === 'chat' ? 'link' : 'link'}
                  onClick={() => setActiveView('chat')}
                  className="px-3 py-1 text-decoration-none"
                  style={{
                    fontWeight: activeView === 'chat' ? '600' : '400',
                    color: activeView === 'chat' ? '#0969da' : '#656d76',
                    borderBottom: activeView === 'chat' ? '2px solid #0969da' : '2px solid transparent',
                    borderRadius: 0,
                  }}
                >
                  <i className="bi bi-chat-dots me-1"></i>
                  Chat
                </Button>
                <Button
                  variant="link"
                  onClick={() => setActiveView('tenants')}
                  className="px-3 py-1 text-decoration-none"
                  style={{
                    fontWeight: activeView === 'tenants' ? '600' : '400',
                    color: activeView === 'tenants' ? '#0969da' : '#656d76',
                    borderBottom: activeView === 'tenants' ? '2px solid #0969da' : '2px solid transparent',
                    borderRadius: 0,
                  }}
                >
                  <i className="bi bi-building me-1"></i>
                  Tenants
                </Button>
              </div>
            </div>
          </Col>
        </Row>
      )}
      <Row className="g-0">
        <Col xs={12}>
          {activeView === 'chat' ? (
            <ChatPage />
          ) : canManageTenants ? (
            <TenantManagementPage />
          ) : (
            <EmptyState
              icon="bi bi-shield-exclamation"
              title="Access Denied"
              description="You don't have permission to access tenant management."
              variant="warning"
            />
          )}
        </Col>
      </Row>
    </Container>
  )
}

export default Dashboard
