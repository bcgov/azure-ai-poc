import type { FC } from 'react'
import { Badge, Spinner } from 'react-bootstrap'
import type { Tenant, TenantStats } from '@/services/tenantService'
import TenantActions from './TenantActions'
import { formatDate, formatBytes, getStatusBadge } from '@/components/tenant/tenantUtils'

interface TenantTableRowProps {
  tenant: Tenant & { stats?: TenantStats }
  onViewStats: (tenant: Tenant) => void
  onCreateSearchIndex: (tenantId: string) => void
  onDeleteSearchIndex: (tenantId: string) => void
}

const TenantTableRow: FC<TenantTableRowProps> = ({
  tenant,
  onViewStats,
  onCreateSearchIndex,
  onDeleteSearchIndex,
}) => {
  return (
    <tr style={{ borderBottom: '0.0625rem solid #e9ecef' }}>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        <strong style={{ color: '#212529' }}>{tenant.name}</strong>
        {tenant.description && (
          <div
            className="text-muted small"
            style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}
          >
            {tenant.description}
          </div>
        )}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        {tenant.display_name}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        {getStatusBadge(tenant.status)}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        {tenant.stats?.user_count ?? <Spinner size="sm" animation="border" />}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        {tenant.stats?.document_count ?? (
          <Spinner size="sm" animation="border" />
        )}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        {tenant.stats?.storage_used_gb !== undefined ? (
          formatBytes(tenant.stats.storage_used_gb * 1024 * 1024 * 1024)
        ) : (
          <Spinner size="sm" animation="border" />
        )}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        {formatDate(tenant.created_at)}
      </td>
      <td style={{ padding: '0.75rem', verticalAlign: 'middle' }}>
        <TenantActions
          tenantId={tenant.id}
          onViewStats={() => onViewStats(tenant)}
          onCreateSearchIndex={() => onCreateSearchIndex(tenant.id)}
          onDeleteSearchIndex={() => onDeleteSearchIndex(tenant.id)}
        />
      </td>
    </tr>
  )
}

export default TenantTableRow
