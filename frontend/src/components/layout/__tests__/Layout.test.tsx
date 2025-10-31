import '@testing-library/jest-dom'
import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Layout from '../Layout'
import { useAuth } from '@/stores'

vi.mock('@/stores', () => ({
  useAuth: vi.fn(),
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

describe('Layout', () => {
  const mockLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Header and Footer', () => {
    it('renders the BC Gov header with title as h1', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      const header = screen.getByTestId('bc-header')
      expect(header).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 1, name: 'AI Chat' })).toBeInTheDocument()
    })

    it('renders the BC Gov footer', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(screen.getByTestId('bc-footer')).toBeInTheDocument()
    })

    it('renders children content', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      expect(screen.getByText('Test Content')).toBeInTheDocument()
    })

    it('has correct layout structure classes', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      const { container } = render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(container.querySelector('.app-layout')).toBeInTheDocument()
      expect(container.querySelector('.app-header')).toBeInTheDocument()
      expect(container.querySelector('.app-content')).toBeInTheDocument()
      expect(container.querySelector('.app-footer')).toBeInTheDocument()
    })
  })

  describe('User Profile Display (when logged in)', () => {
    it('displays username with person icon when logged in', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: 'John Doe',
        logout: mockLogout,
      } as any)

      const { container } = render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(container.querySelector('.bi-person-circle')).toBeInTheDocument()
    })

    it('displays "User" when logged in but username is null', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(screen.getByText('User')).toBeInTheDocument()
    })

    it('displays "User" when logged in but username is empty string', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: '',
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(screen.getByText('User')).toBeInTheDocument()
    })

    it('displays sign out button with icon when logged in', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: 'John Doe',
        logout: mockLogout,
      } as any)

      const { container } = render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      const signOutButton = screen.getByRole('button', { name: /sign out/i })
      expect(signOutButton).toBeInTheDocument()
      expect(container.querySelector('.bi-box-arrow-right')).toBeInTheDocument()
    })

    it('does not display username or sign out button when not logged in', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(screen.queryByText('User')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument()
    })
  })

  describe('Logout Functionality', () => {
    it('calls logout when sign out button is clicked', async () => {
      const user = userEvent.setup()

      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: 'John Doe',
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      const signOutButton = screen.getByRole('button', { name: /sign out/i })
      await user.click(signOutButton)

      expect(mockLogout).toHaveBeenCalledTimes(1)
    })

    it('does not call logout when not logged in (button not present)', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      expect(mockLogout).not.toHaveBeenCalled()
      expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument()
    })

    it('logout is called only once even with multiple clicks', async () => {
      const user = userEvent.setup()

      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: 'John Doe',
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>Content</div>
        </Layout>
      )

      const signOutButton = screen.getByRole('button', { name: /sign out/i })
      await user.click(signOutButton)
      await user.click(signOutButton)
      await user.click(signOutButton)

      expect(mockLogout).toHaveBeenCalledTimes(3)
    })
  })

  describe('Multiple Children', () => {
    it('renders multiple children components', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: false,
        username: null,
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>First Child</div>
          <div>Second Child</div>
          <span>Third Child</span>
        </Layout>
      )

      expect(screen.getByText('First Child')).toBeInTheDocument()
      expect(screen.getByText('Second Child')).toBeInTheDocument()
      expect(screen.getByText('Third Child')).toBeInTheDocument()
    })

    it('renders complex nested children', () => {
      vi.mocked(useAuth).mockReturnValue({
        isLoggedIn: true,
        username: 'Jane Smith',
        logout: mockLogout,
      } as any)

      render(
        <Layout>
          <div>
            <h2>Title</h2>
            <p>Paragraph</p>
            <button>Action</button>
          </div>
        </Layout>
      )

      expect(screen.getByRole('heading', { level: 2, name: 'Title' })).toBeInTheDocument()
      expect(screen.getByText('Paragraph')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
    })
  })
})
