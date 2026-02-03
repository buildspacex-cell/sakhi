/**
 * Sakhi API Client
 * ----------------
 * Handles all communication with the Sakhi API.
 */

import Store from 'electron-store'

const store = new Store()

export interface AgentRegistration {
  agent_name: string
  agent_type: string
  device_id: string
  agent_version: string
  protocol_version: string
  capabilities: string[]
  platform: string
  platform_version?: string
  architecture?: string
}

export interface AgentRegistrationResponse {
  agent_id: string
  auth_token: string
  status: string
  approved_capabilities: string[]
  pending_approval: string[]
  update_available: boolean
  latest_version?: string
}

export interface HeartbeatResponse {
  acknowledged: boolean
  has_pending_actions: boolean
  pending_action_count: number
  update_available: boolean
  update_mandatory: boolean
  latest_version?: string
  commands: Array<{ command: string; parameters: Record<string, unknown> }>
}

export interface AgentAction {
  action_id: string
  action_type: string
  parameters: Record<string, unknown>
  sequence: number
  timeout_ms: number
  description?: string
}

export interface ActionResult {
  action_id: string
  success: boolean
  error?: string
  started_at: string
  completed_at: string
  duration_ms: number
  screenshot_id?: string
  data: Record<string, unknown>
}

export interface ScreenCapture {
  agent_id: string
  session_id?: string
  image_base64: string
  format: string
  width: number
  height: number
  trigger: string
  preceding_action_id?: string
  captured_at: string
  current_app?: string
  current_window_title?: string
}

export interface UpdateInfo {
  has_update: boolean
  latest_version?: string
  download_url?: string
  checksum?: string
  file_size_bytes?: number
  is_mandatory: boolean
  release_notes?: string
}

export class SakhiAPIClient {
  private baseUrl: string
  private agentId: string | null = null
  private authToken: string | null = null
  private personId: string | null = null

  constructor(baseUrl: string = 'http://127.0.0.1:8080') {
    this.baseUrl = baseUrl

    // Restore from storage - check both old format and new 'auth' object format
    const auth = store.get('auth') as { agent_id?: string; auth_token?: string; person_id?: string } | undefined
    if (auth) {
      this.agentId = auth.agent_id || null
      this.authToken = auth.auth_token || null
      this.personId = auth.person_id || null
    } else {
      // Fallback to old format
      this.agentId = store.get('agentId') as string | null
      this.authToken = store.get('authToken') as string | null
      this.personId = store.get('personId') as string | null
    }
  }

  get isRegistered(): boolean {
    return !!(this.agentId && this.authToken)
  }

  get currentAgentId(): string | null {
    return this.agentId
  }

  setPersonId(personId: string): void {
    this.personId = personId
    store.set('personId', personId)
  }

  /**
   * Set agent credentials directly (from device linking flow).
   */
  setAgentCredentials(agentId: string, authToken: string): void {
    this.agentId = agentId
    this.authToken = authToken
    // Store in both formats for compatibility
    store.set('agentId', agentId)
    store.set('authToken', authToken)
    // Also update the 'auth' object
    const auth = store.get('auth') as Record<string, unknown> || {}
    auth.agent_id = agentId
    auth.auth_token = authToken
    store.set('auth', auth)
  }

  /**
   * Clear stored credentials.
   */
  clearCredentials(): void {
    this.agentId = null
    this.authToken = null
    this.personId = null
    store.delete('agentId')
    store.delete('authToken')
    store.delete('personId')
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    }

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`
      headers['X-Agent-Token'] = this.authToken
    }

    if (this.personId) {
      headers['X-Person-Id'] = this.personId
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API error ${response.status}: ${error}`)
    }

    return response.json()
  }

  /**
   * Register this agent with the Sakhi API.
   */
  async register(registration: AgentRegistration): Promise<AgentRegistrationResponse> {
    const result = await this.request<AgentRegistrationResponse>(
      '/api/v1/agent/register',
      {
        method: 'POST',
        body: JSON.stringify(registration),
      }
    )

    // Store credentials
    this.agentId = result.agent_id
    this.authToken = result.auth_token
    store.set('agentId', result.agent_id)
    store.set('authToken', result.auth_token)

    console.log(`[api] Registered as agent ${result.agent_id}`)
    return result
  }

  /**
   * Send heartbeat to API.
   */
  async heartbeat(
    status: string = 'online',
    activeSessionId?: string
  ): Promise<HeartbeatResponse> {
    if (!this.agentId) {
      throw new Error('Agent not registered')
    }

    return this.request<HeartbeatResponse>(
      `/api/v1/agent/${this.agentId}/heartbeat`,
      {
        method: 'POST',
        body: JSON.stringify({
          agent_id: this.agentId,
          status,
          active_session_id: activeSessionId,
        }),
      }
    )
  }

  /**
   * Start a new task session.
   */
  async startSession(taskDescription: string): Promise<{
    session_id: string
    status: string
    initial_actions: AgentAction[]
  }> {
    if (!this.agentId) {
      throw new Error('Agent not registered')
    }

    return this.request(
      `/api/v1/agent/${this.agentId}/session/start`,
      {
        method: 'POST',
        body: JSON.stringify({
          task_description: taskDescription,
        }),
      }
    )
  }

  /**
   * End the current session.
   */
  async endSession(sessionId: string, status: string = 'completed'): Promise<void> {
    if (!this.agentId) {
      throw new Error('Agent not registered')
    }

    await this.request(
      `/api/v1/agent/${this.agentId}/session/${sessionId}/end`,
      {
        method: 'POST',
        body: JSON.stringify({ status }),
      }
    )
  }

  /**
   * Get pending actions to execute.
   */
  async getPendingActions(limit: number = 10): Promise<AgentAction[]> {
    if (!this.agentId) {
      throw new Error('Agent not registered')
    }

    const result = await this.request<{ actions: AgentAction[] }>(
      `/api/v1/agent/${this.agentId}/actions/pending?limit=${limit}`,
      { method: 'GET' }
    )

    return result.actions
  }

  /**
   * Report action execution result.
   */
  async reportActionResult(result: ActionResult): Promise<void> {
    if (!this.agentId) {
      throw new Error('Agent not registered')
    }

    await this.request(
      `/api/v1/agent/${this.agentId}/actions/result`,
      {
        method: 'POST',
        body: JSON.stringify(result),
      }
    )
  }

  /**
   * Submit screenshot for analysis.
   */
  async submitScreenshot(capture: ScreenCapture): Promise<{
    screenshot_id: string
    analysis?: {
      description: string
      detected_elements: Array<Record<string, unknown>>
      ocr_text?: string
    }
  }> {
    if (!this.agentId) {
      throw new Error('Agent not registered')
    }

    return this.request(
      `/api/v1/agent/${this.agentId}/screenshot`,
      {
        method: 'POST',
        body: JSON.stringify(capture),
      }
    )
  }

  /**
   * Check for agent updates.
   */
  async checkUpdate(
    platform: string,
    currentVersion: string,
    architecture?: string
  ): Promise<UpdateInfo> {
    return this.request<UpdateInfo>(
      '/api/v1/agent/update/check',
      {
        method: 'POST',
        body: JSON.stringify({
          agent_type: 'desktop',
          platform,
          current_version: currentVersion,
          architecture,
        }),
      }
    )
  }
}

// Singleton instance
let apiClient: SakhiAPIClient | null = null

export function getAPIClient(baseUrl?: string): SakhiAPIClient {
  if (!apiClient) {
    apiClient = new SakhiAPIClient(
      baseUrl || process.env.SAKHI_API_URL || 'http://127.0.0.1:8080'
    )
  }
  return apiClient
}

export default SakhiAPIClient
