import type { FC, ReactNode } from 'react'

interface EmptyStateProps {
  icon: string
  title: string
  description?: string
  children?: ReactNode
  variant?: 'info' | 'warning' | 'success' | 'danger'
}

const EmptyState: FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  children,
  variant = 'info',
}) => {
  const iconColorClass = {
    info: 'text-primary',
    warning: 'text-warning',
    success: 'text-success',
    danger: 'text-danger',
  }[variant]

  return (
    <div className="empty-state">
      <i className={`${icon} ${iconColorClass} empty-state-icon d-block`}></i>
      <h5>{title}</h5>
      {description && <p>{description}</p>}
      {children}
    </div>
  )
}

export default EmptyState
