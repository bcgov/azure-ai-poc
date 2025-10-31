import type { FC } from 'react'
import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Dropdown,
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

const TenantsListPage: FC = () => {
  const [tenants, setTenants] = useState<TenantWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [page, setPage] = useState(1)
  const [totalTenants, setTotalTenants] = useState(0)

  const loadTenants = async (pageNum: number = 1) => {
    try {
      setLoading(true)
      setError(null)
      const response = await tenantService.getTenants(pageNum, 10)

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
      setTotalTenants(response.total)
      setPage(pageNum)
    } catch (error) {
      console.error('Error loading tenants:', error)
      setError('Failed to load tenants. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteTenant = async () => {
    if (!selectedTenant) return

    try {
      await tenantService.deleteTenant(selectedTenant.id)
      setShowDeleteModal(false)
      setSelectedTenant(null)
      await loadTenants(page)
    } catch (error) {
      console.error('Error deleting tenant:', error)
      setError('Failed to delete tenant. Please try again.')
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

  if (loading && tenants.length === 0) {
    return (
      <Container className="mt-4">
        <div className="text-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
          <p className="mt-2">Loading tenants...</p>
        </div>
      </Container>
    )
  }

  return (
    <Container fluid className="mt-4">
      <Row>
        <Col>
          <div className="d-flex justify-content-between align-items-center mb-4">
            <h1>Tenant Management</h1>
            <Button variant="primary" disabled={true}>
              <i className="bi bi-plus-lg me-2"></i>
              Create Tenant
            </Button>
          </div>

          {error && (
            <Alert variant="danger" dismissible onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Card>
            <Card.Header>
              <Card.Title className="mb-0">Tenants ({totalTenants})</Card.Title>
            </Card.Header>
            <Card.Body className="p-0">
              {tenants.length === 0 ? (
                <div className="text-center py-5">
                  <i
                    className="bi bi-building text-muted"
                    style={{ fontSize: '3rem' }}
                  ></i>
                  <h5 className="text-muted mt-3">No tenants found</h5>
                  <p className="text-muted">
                    Create your first tenant to get started.
                  </p>
                </div>
              ) : (
                <Table responsive striped hover className="mb-0">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Display Name</th>
                      <th>Status</th>
                      <th>Users</th>
                      <th>Documents</th>
                      <th>Storage</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tenants.map((tenant) => (
                      <tr key={tenant.id}>
                        <td>
                          <strong>{tenant.name}</strong>
                          {tenant.description && (
                            <div className="text-muted small">
                              {tenant.description}
                            </div>
                          )}
                        </td>
                        <td>{tenant.display_name}</td>
                        <td>{getStatusBadge(tenant.status)}</td>
                        <td>
                          {tenant.stats?.user_count ?? (
                            <Spinner size="sm" animation="border" />
                          )}
                        </td>
                        <td>
                          {tenant.stats?.document_count ?? (
                            <Spinner size="sm" animation="border" />
                          )}
                        </td>
                        <td>
                          {tenant.stats?.storage_used_gb !== undefined ? (
                            formatBytes(
                              tenant.stats.storage_used_gb * 1024 * 1024 * 1024,
                            )
                          ) : (
                            <Spinner size="sm" animation="border" />
                          )}
                        </td>
                        <td>{formatDate(tenant.created_at)}</td>
                        <td>
                          <Dropdown>
                            <Dropdown.Toggle
                              variant="outline-secondary"
                              size="sm"
                              id={`dropdown-${tenant.id}`}
                            >
                              <i className="bi bi-three-dots-vertical"></i>
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                              <Dropdown.Item href={`/tenants/${tenant.id}`}>
                                <i className="bi bi-eye me-2"></i>
                                View Details
                              </Dropdown.Item>
                              <Dropdown.Item
                                href={`/tenants/${tenant.id}/edit`}
                              >
                                <i className="bi bi-pencil me-2"></i>
                                Edit
                              </Dropdown.Item>
                              <Dropdown.Item
                                href={`/tenants/${tenant.id}/users`}
                              >
                                <i className="bi bi-people me-2"></i>
                                Manage Users
                              </Dropdown.Item>
                              <Dropdown.Item
                                href={`/tenants/${tenant.id}/search-index`}
                              >
                                <i className="bi bi-search me-2"></i>
                                Search Index
                              </Dropdown.Item>
                              <Dropdown.Divider />
                              <Dropdown.Item
                                className="text-danger"
                                onClick={() => {
                                  setSelectedTenant(tenant)
                                  setShowDeleteModal(true)
                                }}
                              >
                                <i className="bi bi-trash me-2"></i>
                                Delete
                              </Dropdown.Item>
                            </Dropdown.Menu>
                          </Dropdown>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>

          {/* Pagination would go here */}
          {totalTenants > 10 && (
            <div className="d-flex justify-content-center mt-3">
              <Button
                variant="outline-primary"
                disabled={page <= 1}
                onClick={() => loadTenants(page - 1)}
                className="me-2"
              >
                Previous
              </Button>
              <span className="align-self-center mx-3">
                Page {page} of {Math.ceil(totalTenants / 10)}
              </span>
              <Button
                variant="outline-primary"
                disabled={page >= Math.ceil(totalTenants / 10)}
                onClick={() => loadTenants(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </Col>
      </Row>

      {/* Delete Confirmation Modal */}
      <Modal show={showDeleteModal} onHide={() => setShowDeleteModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Delete Tenant</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Are you sure you want to delete the tenant{' '}
            <strong>{selectedTenant?.display_name}</strong>?
          </p>
          <Alert variant="warning">
            <i className="bi bi-exclamation-triangle me-2"></i>
            This action cannot be undone. All data associated with this tenant
            will be permanently deleted.
          </Alert>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDeleteTenant}>
            Delete Tenant
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  )
}

export default TenantsListPage
