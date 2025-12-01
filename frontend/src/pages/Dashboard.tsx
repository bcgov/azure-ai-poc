import { EmptyState } from '@/components/common'
import { useAuth } from '@/stores'
import type { FC } from 'react'
import { useState } from 'react'
import { Button, Col, Container, Row } from 'react-bootstrap'
import ChatPage from '@/pages/ChatPage'
import TenantManagementPage from '@/pages/TenantManagementPage'

const Dashboard: FC = () => {
  const [activeView, setActiveView] = useState<'chat' | 'tenants'>('chat')
  const { hasRole } = useAuth()

  const canManageTenants = hasRole(['TENANT_ADMIN'])

  return (
    <Container fluid>
      <Row>
        <Col xs={12}>
          <div className="d-flex justify-content-center mb-4 mt-4">
            <div className="d-flex gap-2">
              <Button
                variant={activeView === 'chat' ? 'primary' : 'outline-primary'}
                onClick={() => setActiveView('chat')}
                className="px-4 py-2"
                style={{
                  fontWeight: '600',
                  borderRadius: '0.75rem',
                  boxShadow:
                    activeView === 'chat'
                      ? '0 0.125rem 0.375rem rgba(13, 110, 253, 0.25)'
                      : '0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.08)',
                  border: activeView === 'chat' ? 'none' : '0.125rem solid #0d6efd',
                }}
              >
                <i className="bi bi-chat-dots me-2"></i>
                AI Chat
              </Button>
              {canManageTenants && (
                <Button
                  variant={activeView === 'tenants' ? 'primary' : 'outline-primary'}
                  onClick={() => setActiveView('tenants')}
                  className="px-4 py-2"
                  style={{
                    fontWeight: '600',
                    borderRadius: '0.75rem',
                    boxShadow:
                      activeView === 'tenants'
                        ? '0 0.125rem 0.375rem rgba(13, 110, 253, 0.25)'
                        : '0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.08)',
                    border: activeView === 'tenants' ? 'none' : '0.125rem solid #0d6efd',
                  }}
                >
                  <i className="bi bi-building me-2"></i>
                  Tenant Management
                </Button>
              )}
            </div>
          </div>
        </Col>
      </Row>
      <Row>
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
