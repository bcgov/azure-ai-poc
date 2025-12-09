/**
 * Source and Citation Utilities
 *
 * Common functions for handling source citations across the application.
 * Provides consistent sorting, formatting, and display helpers for sources.
 */

import type { SourceInfo } from '@/services/chatAgentService'

/**
 * Confidence level ordering (higher = better)
 */
export const CONFIDENCE_ORDER: Record<string, number> = {
  high: 3,
  medium: 2,
  low: 1,
}

/**
 * Get numeric value for confidence level for sorting.
 * Higher values = higher confidence.
 */
export function getConfidenceValue(confidence: string): number {
  return CONFIDENCE_ORDER[confidence?.toLowerCase()] || 0
}

/**
 * Sort sources by confidence level (highest first).
 * Returns a new sorted array, does not mutate the original.
 */
export function sortSourcesByConfidence(sources: SourceInfo[]): SourceInfo[] {
  if (!sources || sources.length === 0) return sources
  return [...sources].sort(
    (a, b) => getConfidenceValue(b.confidence) - getConfidenceValue(a.confidence)
  )
}

/**
 * Get icon class for source type.
 */
export function getSourceIcon(sourceType: string): string {
  switch (sourceType) {
    case 'llm_knowledge':
      return 'bi-cpu'
    case 'document':
      return 'bi-file-text'
    case 'web':
      return 'bi-globe'
    case 'api':
      return 'bi-code-square'
    default:
      return 'bi-question-circle'
  }
}

/**
 * Get color for confidence level (for dots/indicators).
 */
export function getConfidenceColor(confidence: string): string {
  switch (confidence) {
    case 'high':
      return '#16a34a' // green
    case 'medium':
      return '#ca8a04' // yellow/amber
    case 'low':
      return '#dc2626' // red
    default:
      return '#6b7280' // gray
  }
}

/**
 * Get Bootstrap badge variant for confidence level.
 */
export function getConfidenceBadgeVariant(confidence: string): string {
  switch (confidence) {
    case 'high':
      return 'success'
    case 'medium':
      return 'warning'
    case 'low':
      return 'danger'
    default:
      return 'secondary'
  }
}

/**
 * Format source type for display (replaces underscores with spaces).
 */
export function formatSourceType(sourceType: string): string {
  return sourceType.replace(/_/g, ' ')
}

/**
 * Deduplicate sources based on description and URL.
 * Returns sorted by confidence (highest first).
 */
export function deduplicateSources(sources: SourceInfo[]): SourceInfo[] {
  if (!sources || sources.length === 0) return sources

  const seen = new Set<string>()
  const unique: SourceInfo[] = []

  for (const source of sources) {
    const key = `${source.description}|${source.url || ''}`
    if (!seen.has(key)) {
      seen.add(key)
      unique.push(source)
    }
  }

  return sortSourcesByConfidence(unique)
}

/**
 * Get display sources (sorted, optionally limited to top N).
 */
export function getDisplaySources(
  sources: SourceInfo[],
  limit?: number
): { displayed: SourceInfo[]; remaining: number; total: number } {
  const sorted = sortSourcesByConfidence(sources)
  const total = sorted.length

  if (!limit || limit >= total) {
    return { displayed: sorted, remaining: 0, total }
  }

  return {
    displayed: sorted.slice(0, limit),
    remaining: total - limit,
    total,
  }
}
