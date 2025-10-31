import '@testing-library/jest-dom'
import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AuthGuard from '../AuthGuard'
import { useAuth, useAuthInit } from '@/stores'

vi.mock('@/stores', () => ({
  useAuth: vi.fn(),
  useAuthInit: vi.fn(),
}))

describe('AuthGuard', () => {
  const mockLogin = vi.fn()
  const mockHasRole = vi.fn()
  const reloadSpy = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window, 'location', {
      value: { reload: reloadSpy },
      writable: true,
    })
  })

  describe('Loading States', () => {
    it('shows fallback when not initialized', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: false,
        isLoading: true,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard fallback={<div>Custom Loading...</div>}>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Custom Loading...')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('shows default fallback when not initialized and no custom fallback provided', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: false,
        isLoading: true,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Loading...')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('shows fallback when loading', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: true,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard fallback={<div>Still Loading...</div>}>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Still Loading...')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Error States', () => {
    it('shows error alert when initialization fails', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: 'Network connection failed',
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Authentication Error')).toBeInTheDocument()
      expect(screen.getByText(/Failed to initialize authentication:/)).toBeInTheDocument()
      expect(screen.getByText(/Network connection failed/)).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('shows retry button in error state', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: 'Connection timeout',
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      const retryButton = screen.getByRole('button', { name: 'Retry' })
      expect(retryButton).toBeInTheDocument()
    })

    it('reloads page when retry button is clicked', async () => {
      const user = userEvent.setup()

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: 'Connection timeout',
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      const retryButton = screen.getByRole('button', { name: 'Retry' })
      await user.click(retryButton)

      expect(reloadSpy).toHaveBeenCalledTimes(1)
    })
  })

  describe('Not Logged In State', () => {
    it('shows login prompt when not logged in', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Authentication Required')).toBeInTheDocument()
      expect(screen.getByText('Please log in to access this application.')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('shows login button when not logged in', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      const loginButton = screen.getByRole('button', { name: 'Log In' })
      expect(loginButton).toBeInTheDocument()
    })

    it('calls login when login button is clicked', async () => {
      const user = userEvent.setup()

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      const loginButton = screen.getByRole('button', { name: 'Log In' })
      await user.click(loginButton)

      expect(mockLogin).toHaveBeenCalledTimes(1)
    })
  })

  describe('Role-Based Access', () => {
    it('shows access denied when user lacks required role (single role)', () => {
      mockHasRole.mockReturnValue(false)

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles="admin">
          <div>Admin Content</div>
        </AuthGuard>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(screen.getByText(/You don't have the required permissions/)).toBeInTheDocument()
      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
      expect(mockHasRole).toHaveBeenCalledWith('admin')
    })

    it('shows access denied when user lacks required roles (multiple roles)', () => {
      mockHasRole.mockReturnValue(false)

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles={['admin', 'moderator']}>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
      expect(mockHasRole).toHaveBeenCalledWith(['admin', 'moderator'])
    })

    it('renders children when user has required role', () => {
      mockHasRole.mockReturnValue(true)

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles="user">
          <div>User Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('User Content')).toBeInTheDocument()
      expect(screen.queryByText('Access Denied')).not.toBeInTheDocument()
      expect(mockHasRole).toHaveBeenCalledWith('user')
    })

    it('renders children when user has one of the required roles', () => {
      mockHasRole.mockReturnValue(true)

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles={['admin', 'user', 'moderator']}>
          <div>Multi-Role Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Multi-Role Content')).toBeInTheDocument()
      expect(screen.queryByText('Access Denied')).not.toBeInTheDocument()
      expect(mockHasRole).toHaveBeenCalledWith(['admin', 'user', 'moderator'])
    })
  })

  describe('Successful Authentication', () => {
    it('renders children when logged in and no roles required', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      expect(screen.queryByText('Authentication Required')).not.toBeInTheDocument()
    })

    it('renders multiple children when authenticated', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>First Child</div>
          <div>Second Child</div>
          <span>Third Child</span>
        </AuthGuard>
      )

      expect(screen.getByText('First Child')).toBeInTheDocument()
      expect(screen.getByText('Second Child')).toBeInTheDocument()
      expect(screen.getByText('Third Child')).toBeInTheDocument()
    })

    it('renders complex nested children when authenticated', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>
            <h2>Dashboard</h2>
            <p>Welcome back!</p>
            <button>Get Started</button>
          </div>
        </AuthGuard>
      )

      expect(screen.getByRole('heading', { level: 2, name: 'Dashboard' })).toBeInTheDocument()
      expect(screen.getByText('Welcome back!')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Get Started' })).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('does not check roles when requiredRoles is undefined', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles={undefined}>
          <div>Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Content')).toBeInTheDocument()
      expect(mockHasRole).not.toHaveBeenCalled()
    })

    it('handles empty array for requiredRoles', () => {
      mockHasRole.mockReturnValue(false)

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles={[]}>
          <div>Content</div>
        </AuthGuard>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(mockHasRole).toHaveBeenCalledWith([])
    })

    it('prioritizes loading state over error state', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: false,
        isLoading: true,
        error: 'Some error',
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Loading...')).toBeInTheDocument()
      expect(screen.queryByText('Authentication Error')).not.toBeInTheDocument()
    })

    it('prioritizes error state over not logged in state', () => {
      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: 'Init failed',
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard>
          <div>Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Authentication Error')).toBeInTheDocument()
      expect(screen.queryByText('Authentication Required')).not.toBeInTheDocument()
    })

    it('prioritizes not logged in state over role check', () => {
      mockHasRole.mockReturnValue(false)

      vi.mocked(useAuthInit).mockReturnValue({
        isInitialized: true,
        isLoading: false,
        error: null,
      } as any)
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        hasRole: mockHasRole,
        login: mockLogin,
      } as any)

      render(
        <AuthGuard requiredRoles="admin">
          <div>Content</div>
        </AuthGuard>
      )

      expect(screen.getByText('Authentication Required')).toBeInTheDocument()
      expect(screen.queryByText('Access Denied')).not.toBeInTheDocument()
      expect(mockHasRole).not.toHaveBeenCalled()
    })
  })
})
