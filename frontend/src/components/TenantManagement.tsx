import type { FC } from 'react'
import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Modal,
  Row,
  Spinner,
  Table,
} from 'react-bootstrap'
import {
  tenantService,
  type Tenant,
  type TenantStats,
} from '@/services/tenantService'

interface TenantWithStats extends Tenant {
  stats?: TenantStats
}

const TenantManagement: FC = () => {
  const [tenants, setTenants] = useState<TenantWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [showStatsModal, setShowStatsModal] = useState(false)
  const [selectedTenantStats, setSelectedTenantStats] =
    useState<TenantStats | null>(null)

  const loadTenants = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await tenantService.getTenants(1, 20)

      // Load stats for each tenant
      const tenantsWithStats = await Promise.all(
        response.tenants.map(async (tenant) => {
          try {
            const stats = await tenantService.getTenantStats(tenant.id)
            return { ...tenant, stats }
          } catch (error) {
            console.warn(`Failed to load stats for tenant ${tenant.id}:`, error)
            return tenant
          }
        }),
      )

      setTenants(tenantsWithStats)
    } catch (error) {
      console.error('Error loading tenants:', error)
      setError('Failed to load tenants. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSearchIndex = async (tenantId: string) => {
    try {
      await tenantService.createTenantSearchIndex(tenantId)
      alert('Search index created successfully')
      await loadTenants() // Refresh the list
    } catch (error) {
      console.error('Error creating search index:', error)
      alert('Failed to create search index')
    }
  }

  const handleDeleteSearchIndex = async (tenantId: string) => {
    if (confirm('Are you sure you want to delete the search index?')) {
      try {
        await tenantService.deleteTenantSearchIndex(tenantId)
        alert('Search index deleted successfully')
        await loadTenants() // Refresh the list
      } catch (error) {
        console.error('Error deleting search index:', error)
        alert('Failed to delete search index')
      }
    }
  }

  const handleViewStats = async (tenant: Tenant) => {
    try {
      const stats = await tenantService.getTenantStats(tenant.id)
      setSelectedTenant(tenant)
      setSelectedTenantStats(stats)
      setShowStatsModal(true)
    } catch (error) {
      console.error('Error loading tenant stats:', error)
      alert('Failed to load tenant statistics')
    }
  }

  const getStatusBadge = (status: string) => {
    const variant =
      status === 'active'
        ? 'success'
        : status === 'inactive'
          ? 'secondary'
          : 'warning'
    return <Badge bg={variant}>{status}</Badge>
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  useEffect(() => {
    loadTenants()
  }, [])

  if (loading) {
    return (
      <Container fluid style={{ padding: '0 1rem', maxWidth: '87.5rem', margin: '0 auto' }}>
        <div className="empty-state" style={{ minHeight: '25rem' }}>
          <Spinner animation="border" role="status" style={{ width: '3rem', height: '3rem', color: '#003366' }}>
            <span className="visually-hidden">Loading...</span>
          </Spinner>
          <h5 className="mt-3">Loading tenants...</h5>
          <p>Please wait while we fetch the tenant information.</p>
        </div>
      </Container>
    )
  }

  return (
    <Container fluid style={{ padding: '0 1rem', maxWidth: '87.5rem', margin: '0 auto' }}>
      <Row>
        <Col>
          <div 
            className="d-flex justify-content-between align-items-center mb-3 p-3"
            style={{
              background: '#ffffff',
              borderRadius: '0.5rem',
              boxShadow: '0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.08)',
              border: '0.0625rem solid #e9ecef'
            }}
          >
            <h2 className="mb-0" style={{ fontSize: '1.5rem', fontWeight: '600', color: '#212529' }}>
              <i className="bi bi-building me-2 text-primary"></i>
              Tenant Management
            </h2>
            <Button 
              variant="outline-primary" 
              onClick={loadTenants}
              style={{ 
                borderRadius: '0.5rem',
                fontWeight: '600',
                borderWidth: '0.125rem'
              }}
            >
              <i className="bi bi-arrow-clockwise me-2"></i>
              Refresh
            </Button>
          </div>

          {error && (
            <Alert variant="danger" dismissible onClose={() => setError(null)} className="mb-3">
              {error}
            </Alert>
          )}

          <Card className="tenant-card mb-4">
            <Card.Header style={{ background: '#ffffff', borderBottom: '0.0625rem solid #e9ecef' }}>
              <Card.Title className="mb-0 d-flex align-items-center" style={{ fontSize: '1.1rem', fontWeight: '600' }}>
                <i className="bi bi-list-ul me-2 text-primary"></i>
                Tenants ({tenants.length})
              </Card.Title>
            </Card.Header>
            <Card.Body className="p-0" style={{ minHeight: '21.875rem' }}>
              {tenants.length === 0 ? (
                <div className="empty-state">
                  <i className="bi bi-building empty-state-icon"></i>
                  <h5>No tenants found</h5>
                  <p>
                    Contact your administrator to create tenants.
                  </p>
                </div>
              ) : (
                <div className="tenant-table">
                  <Table hover className="mb-0" style={{ fontSize: '0.9rem' }}>
                    <thead style={{ background: '#f8f9fa', borderBottom: '0.125rem solid #dee2e6' }}>
                      <tr>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Name</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Display Name</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Status</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Users</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Documents</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Storage</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Created</th>
                        <th style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.85rem', color: '#495057' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tenants.map((tenant) => (
                      <tr key={tenant.id} style={{ borderBottom: '0.0625rem solid #e9ecef' }}>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
                          <strong style={{ color: '#212529' }}>{tenant.name}</strong>
                          {tenant.description && (
                            <div className="text-muted small" style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>
                              {tenant.description}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>{tenant.display_name}</td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>{getStatusBadge(tenant.status)}</td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
                          {tenant.stats?.user_count ?? (
                            <Spinner size="sm" animation="border" />
                          )}
                        </td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
                          {tenant.stats?.document_count ?? (
                            <Spinner size="sm" animation="border" />
                          )}
                        </td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
                          {tenant.stats?.storage_used_gb !== undefined ? (
                            formatBytes(
                              tenant.stats.storage_used_gb * 1024 * 1024 * 1024,
                            )
                          ) : (
                            <Spinner size="sm" animation="border" />
                          )}
                        </td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>{formatDate(tenant.created_at)}</td>
                        <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
                          <div className="d-flex gap-2">
                            <Button
                              variant="outline-primary"
                              size="sm"
                              onClick={() => handleViewStats(tenant)}
                              title="View Statistics"
                              style={{ 
                                padding: '0.375rem 0.75rem',
                                borderRadius: '0.5rem',
                                transition: 'all 0.2s ease'
                              }}
                            >
                              <i className="bi bi-bar-chart"></i>
                            </Button>
                            <Button
                              variant="outline-success"
                              size="sm"
                              onClick={() => handleCreateSearchIndex(tenant.id)}
                              title="Create Search Index"
                              style={{ 
                                padding: '0.375rem 0.75rem',
                                borderRadius: '0.5rem',
                                transition: 'all 0.2s ease'
                              }}
                            >
                              <i className="bi bi-plus-circle"></i>
                            </Button>
                            <Button
                              variant="outline-danger"
                              size="sm"
                              onClick={() => handleDeleteSearchIndex(tenant.id)}
                              title="Delete Search Index"
                              style={{ 
                                padding: '0.375rem 0.75rem',
                                borderRadius: '0.5rem',
                                transition: 'all 0.2s ease'
                              }}
                            >
                              <i className="bi bi-trash"></i>
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Stats Modal */}
      <Modal
        show={showStatsModal}
        onHide={() => setShowStatsModal(false)}
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title className="d-flex align-items-center">
            <i className="bi bi-bar-chart-fill me-2 text-primary"></i>
            Tenant Statistics - {selectedTenant?.display_name}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedTenantStats && (
            <Row className="g-3">
              <Col md={6}>
                <Card className="stat-card h-100">
                  <Card.Header>
                    <Card.Title className="h6 mb-0 d-flex align-items-center">
                      <i className="bi bi-graph-up me-2 text-primary"></i>
                      Usage Statistics
                    </Card.Title>
                  </Card.Header>
                  <Card.Body>
                    <div className="mb-3 d-flex align-items-center">
                      <i className="bi bi-people-fill text-primary me-2"></i>
                      <strong className="me-2">Users:</strong>
                      <span className="badge bg-primary">{selectedTenantStats.user_count}</span>
                    </div>
                    <div className="mb-3 d-flex align-items-center">
                      <i className="bi bi-file-earmark-text-fill text-info me-2"></i>
                      <strong className="me-2">Documents:</strong>
                      <span className="badge bg-info">{selectedTenantStats.document_count}</span>
                    </div>
                    <div className="mb-3 d-flex align-items-center">
                      <i className="bi bi-database-fill text-warning me-2"></i>
                      <strong className="me-2">Storage Used:</strong>
                      <span className="badge bg-warning text-dark">
                        {formatBytes(
                          selectedTenantStats.storage_used_gb *
                            1024 *
                            1024 *
                            1024,
                        )}
                      </span>
                    </div>
                    <div className="mb-0 d-flex align-items-center">
                      <i className="bi bi-check-circle-fill text-success me-2"></i>
                      <strong className="me-2">Status:</strong>
                      {getStatusBadge(selectedTenantStats.status)}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={6}>
                <Card className="stat-card h-100">
                  <Card.Header>
                    <Card.Title className="h6 mb-0 d-flex align-items-center">
                      <i className="bi bi-clock-history me-2 text-secondary"></i>
                      Activity
                    </Card.Title>
                  </Card.Header>
                  <Card.Body>
                    <div className="mb-3">
                      <i className="bi bi-calendar-event text-secondary me-2"></i>
                      <strong className="me-2">Last Activity:</strong>
                      <span className="text-muted">
                        {selectedTenantStats.last_activity
                          ? formatDate(selectedTenantStats.last_activity)
                          : 'No activity recorded'}
                      </span>
                    </div>
                    <div className="mb-0">
                      <i className="bi bi-hash text-secondary me-2"></i>
                      <strong className="me-2">Tenant ID:</strong>
                      <code className="bg-light p-2 rounded">{selectedTenantStats.tenant_id}</code>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowStatsModal(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  )
}

export default TenantManagement
