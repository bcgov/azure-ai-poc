import { createRootRoute, ErrorComponent, Outlet } from '@tanstack/react-router'
import { Layout, AuthGuard } from '@/components/layout'
import NotFound from '@/components/NotFound'

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
