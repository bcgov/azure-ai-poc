import { createFileRoute } from '@tanstack/react-router'
import { OrchestratorPage } from '@/pages'

export const Route = createFileRoute('/bc-data-query')({
  component: BCDataQuery,
})

function BCDataQuery() {
  return <OrchestratorPage />
}
