import type { FC } from 'react'
import { Button } from 'react-bootstrap'

interface TenantHeaderProps {
  tenantCount: number
  onRefresh: () => void
}

const TenantHeader: FC<TenantHeaderProps> = ({ tenantCount, onRefresh }) => {
  return (
    <div
      className="d-flex justify-content-between align-items-center mb-3 p-3"
      style={{
        background: '#ffffff',
        borderRadius: '0.5rem',
        boxShadow: '0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.08)',
        border: '0.0625rem solid #e9ecef',
      }}
    >
      <h2
        className="mb-0"
        style={{ fontSize: '1.5rem', fontWeight: '600', color: '#212529' }}
      >
        <i className="bi bi-building me-2 text-primary"></i>
        Tenant Management
      </h2>
      <Button
        variant="outline-primary"
        onClick={onRefresh}
        style={{
          borderRadius: '0.5rem',
          fontWeight: '600',
          borderWidth: '0.125rem',
        }}
      >
        <i className="bi bi-arrow-clockwise me-2"></i>
        Refresh
      </Button>
    </div>
  )
}

export default TenantHeader
