import { createRootRoute, ErrorComponent, Outlet } from '@tanstack/react-router'
import Layout from '@/components/Layout'
import NotFound from '@/components/NotFound'
import AuthGuard from '@/components/AuthGuard'

export const Route = createRootRoute({
  component: () => (
    <AuthGuard requiredRoles={['ai-poc-participant']}>
      <Layout>
        <Outlet />
      </Layout>
    </AuthGuard>
  ),
  notFoundComponent: () => <NotFound />,
  errorComponent: ({ error }) => <ErrorComponent error={error} />,
})
