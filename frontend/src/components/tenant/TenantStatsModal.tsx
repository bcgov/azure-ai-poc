import type { FC } from 'react'
import { Modal, Button, Card, Row, Col } from 'react-bootstrap'
import type { Tenant, TenantStats } from '@/services/tenantService'
import { formatDate, formatBytes, getStatusBadge } from './tenantUtils'

interface TenantStatsModalProps {
  show: boolean
  tenant: Tenant | null
  stats: TenantStats | null
  onHide: () => void
}

const TenantStatsModal: FC<TenantStatsModalProps> = ({
  show,
  tenant,
  stats,
  onHide,
}) => {
  return (
    <Modal show={show} onHide={onHide} size="lg">
      <Modal.Header closeButton>
        <Modal.Title className="d-flex align-items-center">
          <i className="bi bi-bar-chart-fill me-2 text-primary"></i>
          Tenant Statistics - {tenant?.display_name}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {stats && (
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
                    <span className="badge bg-primary">{stats.user_count}</span>
                  </div>
                  <div className="mb-3 d-flex align-items-center">
                    <i className="bi bi-file-earmark-text-fill text-info me-2"></i>
                    <strong className="me-2">Documents:</strong>
                    <span className="badge bg-info">{stats.document_count}</span>
                  </div>
                  <div className="mb-3 d-flex align-items-center">
                    <i className="bi bi-database-fill text-warning me-2"></i>
                    <strong className="me-2">Storage Used:</strong>
                    <span className="badge bg-warning text-dark">
                      {formatBytes(stats.storage_used_gb * 1024 * 1024 * 1024)}
                    </span>
                  </div>
                  <div className="mb-0 d-flex align-items-center">
                    <i className="bi bi-check-circle-fill text-success me-2"></i>
                    <strong className="me-2">Status:</strong>
                    {getStatusBadge(stats.status)}
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
                      {stats.last_activity
                        ? formatDate(stats.last_activity)
                        : 'No activity recorded'}
                    </span>
                  </div>
                  <div className="mb-0">
                    <i className="bi bi-hash text-secondary me-2"></i>
                    <strong className="me-2">Tenant ID:</strong>
                    <code className="bg-light p-2 rounded">{stats.tenant_id}</code>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

export default TenantStatsModal
