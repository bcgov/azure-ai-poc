import type { FC } from 'react'
import { Card, Table } from 'react-bootstrap'
import type { Tenant, TenantStats } from '@/services/tenantService'
import TenantTableRow from './TenantTableRow'
import { EmptyState } from '@/components/common'

interface TenantTableProps {
  tenants: Array<Tenant & { stats?: TenantStats }>
  onViewStats: (tenant: Tenant) => void
  onCreateSearchIndex: (tenantId: string) => void
  onDeleteSearchIndex: (tenantId: string) => void
}

const TenantTable: FC<TenantTableProps> = ({
  tenants,
  onViewStats,
  onCreateSearchIndex,
  onDeleteSearchIndex,
}) => {
  return (
    <Card className="tenant-card mb-4">
      <Card.Header
        style={{ background: '#ffffff', borderBottom: '0.0625rem solid #e9ecef' }}
      >
        <Card.Title
          className="mb-0 d-flex align-items-center"
          style={{ fontSize: '1.1rem', fontWeight: '600' }}
        >
          <i className="bi bi-list-ul me-2 text-primary"></i>
          Tenants ({tenants.length})
        </Card.Title>
      </Card.Header>
      <Card.Body className="p-0" style={{ minHeight: '21.875rem' }}>
        {tenants.length === 0 ? (
          <EmptyState
            icon="bi bi-building"
            title="No tenants found"
            description="Contact your administrator to create tenants."
          />
        ) : (
          <div className="tenant-table">
            <Table hover className="mb-0" style={{ fontSize: '0.9rem' }}>
              <thead
                style={{
                  background: '#f8f9fa',
                  borderBottom: '0.125rem solid #dee2e6',
                }}
              >
                <tr>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Name
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Display Name
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Status
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Users
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Documents
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Storage
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Created
                  </th>
                  <th
                    style={{
                      padding: '0.75rem',
                      fontWeight: '600',
                      fontSize: '0.85rem',
                      color: '#495057',
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((tenant) => (
                  <TenantTableRow
                    key={tenant.id}
                    tenant={tenant}
                    onViewStats={onViewStats}
                    onCreateSearchIndex={onCreateSearchIndex}
                    onDeleteSearchIndex={onDeleteSearchIndex}
                  />
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Card.Body>
    </Card>
  )
}

export default TenantTable
