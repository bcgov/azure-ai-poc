import type { FC } from 'react'
import { useState } from 'react'
import { Button, Container, Row, Col } from 'react-bootstrap'
import ChatInterfaceWithDocuments from './ChatInterfaceWithDocuments'
import TenantManagement from './TenantManagement'
import { useAuth } from '../stores'

const Dashboard: FC = () => {
  const [activeView, setActiveView] = useState<'chat' | 'tenants'>('chat')
  const { hasRole } = useAuth()

  // Check if user has admin roles for tenant management
  const canManageTenants = hasRole(['azure-ai-poc-super-admin', 'TENANT_ADMIN'])

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
                  boxShadow: activeView === 'chat' ? '0 0.125rem 0.375rem rgba(0, 51, 102, 0.25)' : '0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.08)',
                  border: activeView === 'chat' ? 'none' : '0.125rem solid #003366'
                }}
              >
                <i className="bi bi-chat-dots me-2"></i>
                AI Chat
              </Button>
              {canManageTenants && (
                <Button
                  variant={
                    activeView === 'tenants' ? 'primary' : 'outline-primary'
                  }
                  onClick={() => setActiveView('tenants')}
                  className="px-4 py-2"
                  style={{ 
                    fontWeight: '600',
                    borderRadius: '0.75rem',
                    boxShadow: activeView === 'tenants' ? '0 0.125rem 0.375rem rgba(0, 51, 102, 0.25)' : '0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.08)',
                    border: activeView === 'tenants' ? 'none' : '0.125rem solid #003366'
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
            <ChatInterfaceWithDocuments />
          ) : canManageTenants ? (
            <TenantManagement />
          ) : (
            <div className="empty-state">
              <i className="bi bi-shield-exclamation text-warning empty-state-icon d-block"></i>
              <h3>Access Denied</h3>
              <p>
                You don't have permission to access tenant management.
              </p>
            </div>
          )}
        </Col>
      </Row>
    </Container>
  )
}

export default Dashboard
