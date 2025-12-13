import '@testing-library/jest-dom'
import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import Layout from '../Layout'
import { useAuth } from '@/components/AuthProvider'

vi.mock('@/components/AuthProvider', () => ({
  useAuth: vi.fn(),
}))

const mockNavigate = vi.fn()
const mockUseLocation = vi.fn()
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => mockUseLocation(),
}))

vi.mock('@bcgov/design-system-react-components', () => ({
  Header: ({ title, titleElement, children }: { title: string; titleElement?: string; children?: React.ReactNode }) => (
    <div data-testid="bc-header">
      {titleElement === 'h1' ? <h1>{title}</h1> : <span>{title}</span>}
      {children}
    </div>
  ),
  Footer: () => <div data-testid="bc-footer">Footer</div>,
}))

describe('Layout (Entra/MSAL)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    mockUseLocation.mockReturnValue({ pathname: '/' })
  })

  it('renders the BC Gov header title as h1', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      user: null,
      roles: [],
      logout: vi.fn(),
    } as any)

    render(
      <Layout>
        <div>Content</div>
      </Layout>,
    )

    expect(screen.getByTestId('bc-header')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 1, name: 'AI POC' }),
    ).toBeInTheDocument()
  })

  it('renders the footer on non-chat pages', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      user: null,
      roles: [],
      logout: vi.fn(),
    } as any)

    mockUseLocation.mockReturnValue({ pathname: '/other-page' })

    render(
      <Layout>
        <div>Content</div>
      </Layout>,
    )

    expect(screen.getByTestId('bc-footer')).toBeInTheDocument()
  })

  it('renders user info and sign out button when authenticated', () => {
    const mockLogout = vi.fn()
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      user: { name: 'John Doe', username: 'john@example.com' },
      roles: ['ai-poc-participant'],
      logout: mockLogout,
    } as any)

    render(
      <Layout>
        <div>Content</div>
      </Layout>,
    )

    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument()
  })
})
