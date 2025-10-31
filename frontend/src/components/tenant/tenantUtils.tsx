import { Badge } from 'react-bootstrap'

export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString()
}

export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const getStatusBadge = (status: string) => {
  const variant =
    status === 'active'
      ? 'success'
      : status === 'inactive'
        ? 'secondary'
        : 'warning'
  return <Badge bg={variant}>{status}</Badge>
}
