import { createFileRoute } from '@tanstack/react-router'
import { MCPManager } from '../components/MCPManager'

export const Route = createFileRoute('/mcp')({
  component: MCPPage,
})

function MCPPage() {
  return (
    <div className="container-fluid py-4">
      <MCPManager />
    </div>
  )
}
