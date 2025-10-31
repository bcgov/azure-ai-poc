import type { FC } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  Alert,
  Button,
  Card,
  Col,
  Container,
  Form,
  Row,
  Spinner,
} from 'react-bootstrap'
import {
  tenantService,
  type CreateTenantRequest,
  type UpdateTenantRequest,
} from '@/services/tenantService'

interface TenantFormData {
  name: string
  display_name: string
  description: string
  status: 'active' | 'inactive' | 'suspended'
  max_users: string
  max_documents: string
  max_storage_gb: string
}

interface TenantFormPageProps {
  tenantId?: string
}

const TenantFormPage: FC<TenantFormPageProps> = ({ tenantId }) => {
  const navigate = useNavigate()
  const isEditing = Boolean(tenantId)

  const [formData, setFormData] = useState<TenantFormData>({
    name: '',
    display_name: '',
    description: '',
    status: 'active',
    max_users: '',
    max_documents: '',
    max_storage_gb: '',
  })

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({})

  const loadTenant = async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const tenant = await tenantService.getTenant(id)

      setFormData({
        name: tenant.name,
        display_name: tenant.display_name,
        description: tenant.description || '',
        status: tenant.status,
        max_users: tenant.quotas?.max_users?.toString() || '',
        max_documents: tenant.quotas?.max_documents?.toString() || '',
        max_storage_gb: tenant.quotas?.max_storage_gb?.toString() || '',
      })
    } catch (error) {
      console.error('Error loading tenant:', error)
      setError('Failed to load tenant details. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!formData.name.trim()) {
      errors.name = 'Name is required'
    } else if (!/^[a-z0-9-]+$/.test(formData.name)) {
      errors.name =
        'Name must contain only lowercase letters, numbers, and hyphens'
    }

    if (!formData.display_name.trim()) {
      errors.display_name = 'Display name is required'
    }

    if (formData.max_users && isNaN(Number(formData.max_users))) {
      errors.max_users = 'Must be a valid number'
    }

    if (formData.max_documents && isNaN(Number(formData.max_documents))) {
      errors.max_documents = 'Must be a valid number'
    }

    if (formData.max_storage_gb && isNaN(Number(formData.max_storage_gb))) {
      errors.max_storage_gb = 'Must be a valid number'
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      setSaving(true)
      setError(null)

      const quotas = {
        ...(formData.max_users && { max_users: Number(formData.max_users) }),
        ...(formData.max_documents && {
          max_documents: Number(formData.max_documents),
        }),
        ...(formData.max_storage_gb && {
          max_storage_gb: Number(formData.max_storage_gb),
        }),
      }

      if (isEditing && tenantId) {
        const updateData: UpdateTenantRequest = {
          display_name: formData.display_name,
          description: formData.description || undefined,
          status: formData.status,
          ...(Object.keys(quotas).length > 0 && { quotas }),
        }
        await tenantService.updateTenant(tenantId, updateData)
      } else {
        const createData: CreateTenantRequest = {
          name: formData.name,
          display_name: formData.display_name,
          description: formData.description || undefined,
          ...(Object.keys(quotas).length > 0 && { quotas }),
        }
        await tenantService.createTenant(createData)
      }

      navigate({ to: '/tenants' })
    } catch (error: any) {
      console.error('Error saving tenant:', error)
      setError(
        error.response?.data?.detail ||
          `Failed to ${isEditing ? 'update' : 'create'} tenant. Please try again.`,
      )
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (field: keyof TenantFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))

    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors((prev) => ({ ...prev, [field]: '' }))
    }
  }

  useEffect(() => {
    if (isEditing && tenantId) {
      loadTenant(tenantId)
    }
  }, [isEditing, tenantId])

  if (loading) {
    return (
      <Container className="mt-4">
        <div className="text-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
          <p className="mt-2">Loading tenant details...</p>
        </div>
      </Container>
    )
  }

  return (
    <Container className="mt-4">
      <Row>
        <Col md={8} lg={6} className="mx-auto">
          <div className="d-flex align-items-center mb-4">
            <Button
              variant="outline-secondary"
              onClick={() => navigate({ to: '/tenants' })}
              className="me-3"
            >
              <i className="bi bi-arrow-left"></i>
            </Button>
            <h1>{isEditing ? 'Edit Tenant' : 'Create Tenant'}</h1>
          </div>

          {error && (
            <Alert variant="danger" dismissible onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Card>
            <Card.Header>
              <Card.Title className="mb-0">
                {isEditing ? 'Tenant Details' : 'New Tenant'}
              </Card.Title>
            </Card.Header>
            <Card.Body>
              <Form onSubmit={handleSubmit}>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>
                        Name <span className="text-danger">*</span>
                      </Form.Label>
                      <Form.Control
                        type="text"
                        value={formData.name}
                        onChange={(e) =>
                          handleInputChange('name', e.target.value)
                        }
                        isInvalid={!!validationErrors.name}
                        disabled={isEditing}
                        placeholder="my-tenant"
                      />
                      <Form.Control.Feedback type="invalid">
                        {validationErrors.name}
                      </Form.Control.Feedback>
                      {!isEditing && (
                        <Form.Text className="text-muted">
                          Lowercase letters, numbers, and hyphens only. Cannot
                          be changed later.
                        </Form.Text>
                      )}
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>
                        Display Name <span className="text-danger">*</span>
                      </Form.Label>
                      <Form.Control
                        type="text"
                        value={formData.display_name}
                        onChange={(e) =>
                          handleInputChange('display_name', e.target.value)
                        }
                        isInvalid={!!validationErrors.display_name}
                        placeholder="My Tenant"
                      />
                      <Form.Control.Feedback type="invalid">
                        {validationErrors.display_name}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                </Row>

                <Form.Group className="mb-3">
                  <Form.Label>Description</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={formData.description}
                    onChange={(e) =>
                      handleInputChange('description', e.target.value)
                    }
                    placeholder="Brief description of this tenant..."
                  />
                </Form.Group>

                {isEditing && (
                  <Form.Group className="mb-3">
                    <Form.Label>Status</Form.Label>
                    <Form.Select
                      value={formData.status}
                      onChange={(e) =>
                        handleInputChange('status', e.target.value)
                      }
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="suspended">Suspended</option>
                    </Form.Select>
                  </Form.Group>
                )}

                <Card className="border-secondary">
                  <Card.Header className="bg-light">
                    <Card.Title className="mb-0 h6">Resource Quotas</Card.Title>
                  </Card.Header>
                  <Card.Body>
                    <Row>
                      <Col md={4}>
                        <Form.Group className="mb-3">
                          <Form.Label>Max Users</Form.Label>
                          <Form.Control
                            type="number"
                            value={formData.max_users}
                            onChange={(e) =>
                              handleInputChange('max_users', e.target.value)
                            }
                            isInvalid={!!validationErrors.max_users}
                            placeholder="Unlimited"
                            min="1"
                          />
                          <Form.Control.Feedback type="invalid">
                            {validationErrors.max_users}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                      <Col md={4}>
                        <Form.Group className="mb-3">
                          <Form.Label>Max Documents</Form.Label>
                          <Form.Control
                            type="number"
                            value={formData.max_documents}
                            onChange={(e) =>
                              handleInputChange('max_documents', e.target.value)
                            }
                            isInvalid={!!validationErrors.max_documents}
                            placeholder="Unlimited"
                            min="1"
                          />
                          <Form.Control.Feedback type="invalid">
                            {validationErrors.max_documents}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                      <Col md={4}>
                        <Form.Group className="mb-3">
                          <Form.Label>Max Storage (GB)</Form.Label>
                          <Form.Control
                            type="number"
                            value={formData.max_storage_gb}
                            onChange={(e) =>
                              handleInputChange(
                                'max_storage_gb',
                                e.target.value,
                              )
                            }
                            isInvalid={!!validationErrors.max_storage_gb}
                            placeholder="Unlimited"
                            min="1"
                            step="0.1"
                          />
                          <Form.Control.Feedback type="invalid">
                            {validationErrors.max_storage_gb}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                    </Row>
                    <Form.Text className="text-muted">
                      Leave blank for unlimited quotas. These can be adjusted
                      later.
                    </Form.Text>
                  </Card.Body>
                </Card>

                <div className="d-flex justify-content-end gap-2 mt-4">
                  <Button
                    variant="secondary"
                    onClick={() => navigate({ to: '/tenants' })}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" disabled={saving}>
                    {saving ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        {isEditing ? 'Updating...' : 'Creating...'}
                      </>
                    ) : (
                      <>{isEditing ? 'Update Tenant' : 'Create Tenant'}</>
                    )}
                  </Button>
                </div>
              </Form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default TenantFormPage
