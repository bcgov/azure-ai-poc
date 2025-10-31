import { createFileRoute } from '@tanstack/react-router'
import TenantManagement from '@/components/TenantManagement'

export const Route = createFileRoute('/tenants')({
  component: TenantsPage,
})

function TenantsPage() {
  return <TenantManagement />
}
