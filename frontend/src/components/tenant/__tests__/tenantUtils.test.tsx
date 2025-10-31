import '@testing-library/jest-dom'
import { describe, it, expect } from 'vitest'
import { formatDate, formatBytes, getStatusBadge } from '@/components/tenant/tenantUtils'
import { render } from '@testing-library/react'

describe('tenantUtils', () => {
  describe('formatDate', () => {
    it('should format date string to locale date string', () => {
      const dateString = '2024-01-15T10:30:00Z'
      const result = formatDate(dateString)
      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('should handle different date formats', () => {
      const dateString = '2024-12-31T23:59:59Z'
      const result = formatDate(dateString)
      expect(result).toBeTruthy()
    })
  })

  describe('formatBytes', () => {
    it('should return "0 Bytes" for 0 bytes', () => {
      expect(formatBytes(0)).toBe('0 Bytes')
    })

    it('should format bytes correctly', () => {
      expect(formatBytes(1024)).toBe('1 KB')
      expect(formatBytes(1024 * 1024)).toBe('1 MB')
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB')
    })

    it('should format decimal values correctly', () => {
      expect(formatBytes(1536)).toBe('1.5 KB')
      expect(formatBytes(1024 * 1024 * 1.5)).toBe('1.5 MB')
    })

    it('should handle large values', () => {
      const result = formatBytes(1024 * 1024 * 1024 * 2.5)
      expect(result).toBe('2.5 GB')
    })

    it('should handle small values', () => {
      expect(formatBytes(512)).toBe('512 Bytes')
      expect(formatBytes(100)).toBe('100 Bytes')
    })
  })

  describe('getStatusBadge', () => {
    it('should return success badge for active status', () => {
      const { container } = render(getStatusBadge('active'))
      const badge = container.querySelector('.badge')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('bg-success')
      expect(badge).toHaveTextContent('active')
    })

    it('should return secondary badge for inactive status', () => {
      const { container } = render(getStatusBadge('inactive'))
      const badge = container.querySelector('.badge')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('bg-secondary')
      expect(badge).toHaveTextContent('inactive')
    })

    it('should return warning badge for other statuses', () => {
      const { container } = render(getStatusBadge('pending'))
      const badge = container.querySelector('.badge')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('bg-warning')
      expect(badge).toHaveTextContent('pending')
    })

    it('should handle unknown status', () => {
      const { container } = render(getStatusBadge('unknown'))
      const badge = container.querySelector('.badge')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveClass('bg-warning')
    })
  })
})
