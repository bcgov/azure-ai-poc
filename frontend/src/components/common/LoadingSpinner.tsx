import type { FC } from 'react'
import { Spinner } from 'react-bootstrap'

interface LoadingSpinnerProps {
  size?: 'sm'
  message?: string
  className?: string
}

const LoadingSpinner: FC<LoadingSpinnerProps> = ({
  size,
  message,
  className = '',
}) => {
  return (
    <div className={`d-flex align-items-center ${className}`}>
      <Spinner animation="border" size={size} className="me-2" />
      {message && <span className="text-muted">{message}</span>}
    </div>
  )
}

export default LoadingSpinner
