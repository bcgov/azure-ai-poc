import type { FC } from 'react'
import { Button } from 'react-bootstrap'

interface TenantActionsProps {
  tenantId: string
  onViewStats: () => void
  onCreateSearchIndex: () => void
  onDeleteSearchIndex: () => void
}

const TenantActions: FC<TenantActionsProps> = ({
  onViewStats,
  onCreateSearchIndex,
  onDeleteSearchIndex,
}) => {
  return (
    <div className="d-flex gap-2">
      <Button
        variant="outline-primary"
        size="sm"
        onClick={onViewStats}
        title="View Statistics"
        style={{
          padding: '0.375rem 0.75rem',
          borderRadius: '0.5rem',
          transition: 'all 0.2s ease',
        }}
      >
        <i className="bi bi-bar-chart"></i>
      </Button>
      <Button
        variant="outline-success"
        size="sm"
        onClick={onCreateSearchIndex}
        title="Create Search Index"
        style={{
          padding: '0.375rem 0.75rem',
          borderRadius: '0.5rem',
          transition: 'all 0.2s ease',
        }}
      >
        <i className="bi bi-plus-circle"></i>
      </Button>
      <Button
        variant="outline-danger"
        size="sm"
        onClick={onDeleteSearchIndex}
        title="Delete Search Index"
        style={{
          padding: '0.375rem 0.75rem',
          borderRadius: '0.5rem',
          transition: 'all 0.2s ease',
        }}
      >
        <i className="bi bi-trash"></i>
      </Button>
    </div>
  )
}

export default TenantActions
