import '@testing-library/jest-dom'
import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import AuthGuard from '../AuthGuard'
import { useAuth } from '@/components/AuthProvider'

vi.mock('@/components/AuthProvider', () => ({
  useAuth: vi.fn(),
}))

describe('AuthGuard (Entra/MSAL)', () => {
  const mockLogin = vi.fn()
  const reloadSpy = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window, 'location', {
      value: { reload: reloadSpy },
      writable: true,
    })
  })

  it('shows fallback while initializing/loading', () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: false,
      isLoading: true,
      error: null,
      isAuthenticated: false,
      user: null,
      roles: [],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    render(
      <AuthGuard fallback={<div>Custom Loading...</div>}>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Custom Loading...')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('shows error alert when initialization fails and retries reload', async () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: 'Network connection failed',
      isAuthenticated: false,
      user: null,
      roles: [],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    const user = userEvent.setup()
    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Authentication Error')).toBeInTheDocument()
    expect(
      screen.getByText(/Failed to initialize authentication:/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Network connection failed/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(reloadSpy).toHaveBeenCalled()
  })

  it('prompts login when unauthenticated', async () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      isAuthenticated: false,
      user: null,
      roles: [],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    const user = userEvent.setup()
    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Authentication Required')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Log In' }))
    expect(mockLogin).toHaveBeenCalled()
  })

  it('denies access when required role missing', () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      isAuthenticated: true,
      user: { name: 'Test User', username: 'test@example.com' },
      roles: ['some-other-role'],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    render(
      <AuthGuard requiredRoles={['ai-poc-participant']}>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Access Denied')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when authenticated and role present', () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      isAuthenticated: true,
      user: { name: 'Test User', username: 'test@example.com' },
      roles: ['ai-poc-participant'],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    render(
      <AuthGuard requiredRoles={['ai-poc-participant']}>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('renders children when authenticated and no roles are required', () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      isAuthenticated: true,
      user: { name: 'Test User', username: 'test@example.com' },
      roles: [],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('treats an empty requiredRoles array as no role requirement', () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      isAuthenticated: true,
      user: { name: 'Test User', username: 'test@example.com' },
      roles: [],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    render(
      <AuthGuard requiredRoles={[]}>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('denies access when multiple required roles are provided and one is missing', () => {
    vi.mocked(useAuth).mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      isAuthenticated: true,
      user: { name: 'Test User', username: 'test@example.com' },
      roles: ['role-a'],
      login: mockLogin,
      logout: vi.fn(),
    } as any)

    render(
      <AuthGuard requiredRoles={['role-a', 'role-b']}>
        <div>Protected Content</div>
      </AuthGuard>,
    )

    expect(screen.getByText('Access Denied')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })
})
