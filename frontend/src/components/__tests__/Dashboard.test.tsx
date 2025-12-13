import '@testing-library/jest-dom'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import { useAuth } from '@/components/AuthProvider'
import Dashboard from '@/components/Dashboard'

vi.mock('@/components/AuthProvider', () => ({
  useAuth: vi.fn(),
}))

describe('Dashboard', () => {
  it('renders the AI Chat button', () => {
    vi.mocked(useAuth).mockReturnValue({ roles: [] } as any)
    render(<Dashboard />)
    expect(screen.getByRole('button', { name: /AI Chat/i })).toBeInTheDocument()
  })
})
