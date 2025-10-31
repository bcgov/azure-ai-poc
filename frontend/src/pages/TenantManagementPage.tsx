import type { FC } from 'react'
import { useEffect, useState } from 'react'
import { Alert, Container, Row, Col } from 'react-bootstrap'
import {
  tenantService,
  type Tenant,
  type TenantStats,
} from '@/services/tenantService'
import {
  TenantHeader,
  TenantTable,
  TenantStatsModal,
} from '@/components/tenant'
import { EmptyState, LoadingSpinner } from '@/components/common'

interface TenantWithStats extends Tenant {
  stats?: TenantStats
}

const TenantManagementPage: FC = () => {
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
      await loadTenants()
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
        await loadTenants()
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

  useEffect(() => {
    loadTenants()
  }, [])

  if (loading) {
    return (
      <Container
        fluid
        style={{ padding: '0 1rem', maxWidth: '87.5rem', margin: '0 auto' }}
      >
        <EmptyState
          icon="bi bi-hourglass-split"
          title="Loading tenants..."
          description="Please wait while we fetch the tenant information."
        >
          <div className="mt-3">
            <LoadingSpinner size="sm" />
          </div>
        </EmptyState>
      </Container>
    )
  }

  return (
    <Container
      fluid
      style={{ padding: '0 1rem', maxWidth: '87.5rem', margin: '0 auto' }}
    >
      <Row>
        <Col>
          <TenantHeader tenantCount={tenants.length} onRefresh={loadTenants} />

          {error && (
            <Alert
              variant="danger"
              dismissible
              onClose={() => setError(null)}
              className="mb-3"
            >
              {error}
            </Alert>
          )}

          <TenantTable
            tenants={tenants}
            onViewStats={handleViewStats}
            onCreateSearchIndex={handleCreateSearchIndex}
            onDeleteSearchIndex={handleDeleteSearchIndex}
          />
        </Col>
      </Row>

      <TenantStatsModal
        show={showStatsModal}
        tenant={selectedTenant}
        stats={selectedTenantStats}
        onHide={() => setShowStatsModal(false)}
      />
    </Container>
  )
}

export default TenantManagementPage
