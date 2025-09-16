/**
 * React component for MCP (Model Context Protocol) management
 */

import React, { useState, useEffect } from 'react'
import { Card, Button, Alert, Spinner, Form, Modal } from 'react-bootstrap'
import {
  mcpService,
  MCPTool,
  MCPPrompt,
  MCPResource,
} from '../services/mcpService'

interface MCPManagerProps {
  className?: string
}

export const MCPManager: React.FC<MCPManagerProps> = ({ className = '' }) => {
  const [connectedServers, setConnectedServers] = useState<string[]>([])
  const [internalTools, setInternalTools] = useState<MCPTool[]>([])
  const [selectedServer, setSelectedServer] = useState<string>('')
  const [serverTools, setServerTools] = useState<MCPTool[]>([])
  const [serverPrompts, setServerPrompts] = useState<MCPPrompt[]>([])
  const [serverResources, setServerResources] = useState<MCPResource[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Connection modal state
  const [showConnectModal, setShowConnectModal] = useState(false)
  const [newServerName, setNewServerName] = useState('')
  const [newServerCommand, setNewServerCommand] = useState('')

  // Tool execution
  const [toolResults, setToolResults] = useState<any>(null)
  const [showToolModal, setShowToolModal] = useState(false)
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null)
  const [toolArguments, setToolArguments] = useState<Record<string, any>>({})

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [servers, tools] = await Promise.all([
        mcpService.getConnectedServers(),
        mcpService.getInternalTools(),
      ])

      setConnectedServers(servers)
      setInternalTools(tools)

      if (servers.length > 0 && !selectedServer) {
        setSelectedServer(servers[0])
        await loadServerDetails(servers[0])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP data')
    } finally {
      setLoading(false)
    }
  }

  const loadServerDetails = async (serverName: string) => {
    try {
      setLoading(true)

      const [tools, prompts, resources] = await Promise.all([
        mcpService.getTools(serverName),
        mcpService.getPrompts(serverName),
        mcpService.getResources(serverName),
      ])

      setServerTools(tools)
      setServerPrompts(prompts)
      setServerResources(resources)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load server details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleServerChange = async (serverName: string) => {
    setSelectedServer(serverName)
    if (serverName) {
      await loadServerDetails(serverName)
    }
  }

  const handleConnectToServer = async () => {
    try {
      setLoading(true)
      setError(null)

      const command = newServerCommand.split(' ').filter((cmd: string) => cmd.trim())
      await mcpService.connectToServer(newServerName, command)

      setSuccess(`Successfully connected to ${newServerName}`)
      setShowConnectModal(false)
      setNewServerName('')
      setNewServerCommand('')
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  const handleDisconnectFromServer = async (serverName: string) => {
    try {
      setLoading(true)
      setError(null)

      await mcpService.disconnectFromServer(serverName)
      setSuccess(`Disconnected from ${serverName}`)

      if (selectedServer === serverName) {
        setSelectedServer('')
        setServerTools([])
        setServerPrompts([])
        setServerResources([])
      }

      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect from server')
    } finally {
      setLoading(false)
    }
  }

  const handleToolCall = async () => {
    if (!selectedTool) return

    try {
      setLoading(true)
      setError(null)

      const result = await mcpService.callTool(
        selectedServer || 'internal',
        selectedTool.name,
        toolArguments
      )

      setToolResults(result)
      setSuccess(`Tool ${selectedTool.name} executed successfully`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute tool')
    } finally {
      setLoading(false)
    }
  }

  const clearMessages = () => {
    setError(null)
    setSuccess(null)
  }

  return (
    <div className={`mcp-manager ${className}`}>
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h4>MCP Manager</h4>
          <Button
            variant="primary"
            onClick={() => setShowConnectModal(true)}
            disabled={loading}
          >
            Connect to Server
          </Button>
        </Card.Header>

        <Card.Body>
          {loading && (
            <div className="text-center my-3">
              <Spinner animation="border" role="status">
                <span className="visually-hidden">Loading...</span>
              </Spinner>
            </div>
          )}

          {error && (
            <Alert variant="danger" dismissible onClose={clearMessages}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert variant="success" dismissible onClose={clearMessages}>
              {success}
            </Alert>
          )}

          {/* Connected Servers */}
          <div className="mb-4">
            <h5>Connected Servers</h5>
            {connectedServers.length === 0 ? (
              <p className="text-muted">No servers connected</p>
            ) : (
              <div className="d-flex flex-wrap gap-2">
                {connectedServers.map((server) => (
                  <div key={server} className="d-flex align-items-center gap-2">
                    <Button
                      variant={selectedServer === server ? 'primary' : 'outline-primary'}
                      size="sm"
                      onClick={() => handleServerChange(server)}
                    >
                      {server}
                    </Button>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => handleDisconnectFromServer(server)}
                      disabled={loading}
                    >
                      ×
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Internal Tools */}
          <div className="mb-4">
            <h5>Internal Tools</h5>
            {internalTools.length === 0 ? (
              <p className="text-muted">No internal tools available</p>
            ) : (
              <div className="row">
                {internalTools.map((tool) => (
                  <div key={tool.name} className="col-md-6 mb-3">
                    <Card>
                      <Card.Body>
                        <Card.Title>{tool.name}</Card.Title>
                        <Card.Text>{tool.description}</Card.Text>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            setSelectedTool(tool)
                            setToolArguments({})
                            setShowToolModal(true)
                          }}
                        >
                          Execute
                        </Button>
                      </Card.Body>
                    </Card>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Server Details */}
          {selectedServer && (
            <div className="mb-4">
              <h5>Server: {selectedServer}</h5>

              {/* Tools */}
              <div className="mb-3">
                <h6>Tools</h6>
                {serverTools.length === 0 ? (
                  <p className="text-muted">No tools available</p>
                ) : (
                  <div className="row">
                    {serverTools.map((tool) => (
                      <div key={tool.name} className="col-md-6 mb-3">
                        <Card>
                          <Card.Body>
                            <Card.Title>{tool.name}</Card.Title>
                            <Card.Text>{tool.description}</Card.Text>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => {
                                setSelectedTool(tool)
                                setToolArguments({})
                                setShowToolModal(true)
                              }}
                            >
                              Execute
                            </Button>
                          </Card.Body>
                        </Card>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Prompts */}
              <div className="mb-3">
                <h6>Prompts</h6>
                {serverPrompts.length === 0 ? (
                  <p className="text-muted">No prompts available</p>
                ) : (
                  <div className="list-group">
                    {serverPrompts.map((prompt) => (
                      <div key={prompt.name} className="list-group-item">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <h6 className="mb-1">{prompt.name}</h6>
                            <p className="mb-1">{prompt.description}</p>
                          </div>
                          <Button variant="outline-primary" size="sm">
                            Use Prompt
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Resources */}
              <div className="mb-3">
                <h6>Resources</h6>
                {serverResources.length === 0 ? (
                  <p className="text-muted">No resources available</p>
                ) : (
                  <div className="list-group">
                    {serverResources.map((resource) => (
                      <div key={resource.uri} className="list-group-item">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <h6 className="mb-1">{resource.name}</h6>
                            <p className="mb-1">{resource.description}</p>
                            <small className="text-muted">{resource.uri}</small>
                          </div>
                          <Button variant="outline-primary" size="sm">
                            Read
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tool Results */}
          {toolResults && (
            <div className="mb-4">
              <h5>Tool Results</h5>
              <Card>
                <Card.Body>
                  <pre className="mb-0">{JSON.stringify(toolResults, null, 2)}</pre>
                </Card.Body>
              </Card>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Connect Modal */}
      <Modal show={showConnectModal} onHide={() => setShowConnectModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Connect to MCP Server</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Server Name</Form.Label>
              <Form.Control
                type="text"
                value={newServerName}
                onChange={(e) => setNewServerName(e.target.value)}
                placeholder="Enter server name"
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Command</Form.Label>
              <Form.Control
                type="text"
                value={newServerCommand}
                onChange={(e) => setNewServerCommand(e.target.value)}
                placeholder="Enter server command (e.g., python server.py)"
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowConnectModal(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConnectToServer}
            disabled={!newServerName || !newServerCommand || loading}
          >
            Connect
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Tool Execution Modal */}
      <Modal show={showToolModal} onHide={() => setShowToolModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Execute Tool: {selectedTool?.name}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedTool && (
            <div>
              <p>{selectedTool.description}</p>
              <Form>
                {selectedTool.inputSchema?.properties &&
                  Object.entries(selectedTool.inputSchema.properties).map(([key, schema]) => (
                    <Form.Group key={key} className="mb-3">
                      <Form.Label>{key}</Form.Label>
                      <Form.Control
                        type="text"
                        value={toolArguments[key] || ''}
                        onChange={(e) =>
                          setToolArguments({ ...toolArguments, [key]: e.target.value })
                        }
                        placeholder={`Enter ${key}`}
                      />
                      {schema.description && (
                        <Form.Text className="text-muted">{schema.description}</Form.Text>
                      )}
                    </Form.Group>
                  ))}
              </Form>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowToolModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleToolCall} disabled={loading}>
            Execute
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}