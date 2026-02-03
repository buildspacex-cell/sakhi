/**
 * Sakhi Desktop Agent
 * -------------------
 * Main agent logic: registration, heartbeat, action loop.
 */

import { app } from 'electron'
import { v4 as uuidv4 } from 'uuid'
import Store from 'electron-store'
import {
  getAPIClient,
  SakhiAPIClient,
  AgentAction,
  ActionResult,
} from './api'
import { executeAction, executeActionBatch } from './actions'
import {
  captureScreen,
  captureToBase64,
  getActiveWindow,
  CaptureResult,
} from './screen'
import {
  initUpdater,
  checkForUpdate,
  promptForUpdate,
  downloadUpdate,
  installUpdate,
} from './updater'

const store = new Store()

// Agent configuration
const AGENT_VERSION = '1.0.0'
const PROTOCOL_VERSION = '1.0'
const HEARTBEAT_INTERVAL_MS = 30000 // 30 seconds
const ACTION_POLL_INTERVAL_MS = 1000 // 1 second when active

export interface AgentState {
  status: 'idle' | 'registered' | 'active' | 'executing' | 'paused' | 'error'
  agentId: string | null
  sessionId: string | null
  currentTask: string | null
  lastHeartbeat: Date | null
  actionsExecuted: number
  lastError: string | null
}

type StateListener = (state: AgentState) => void

class SakhiAgent {
  private api: SakhiAPIClient
  private state: AgentState
  private heartbeatInterval: NodeJS.Timeout | null = null
  private actionPollInterval: NodeJS.Timeout | null = null
  private listeners: Set<StateListener> = new Set()
  private deviceId: string

  constructor() {
    this.api = getAPIClient()
    this.deviceId = this.getOrCreateDeviceId()
    this.state = {
      status: 'idle',
      agentId: null,
      sessionId: null,
      currentTask: null,
      lastHeartbeat: null,
      actionsExecuted: 0,
      lastError: null,
    }
  }

  /**
   * Get or create a unique device identifier.
   */
  private getOrCreateDeviceId(): string {
    let deviceId = store.get('deviceId') as string | undefined
    if (!deviceId) {
      deviceId = uuidv4()
      store.set('deviceId', deviceId)
    }
    return deviceId
  }

  /**
   * Get agent capabilities based on platform.
   */
  private getCapabilities(): string[] {
    const base = [
      'screen_capture',
      'mouse_click',
      'mouse_move',
      'keyboard_type',
      'keyboard_shortcut',
      'scroll',
      'clipboard_write',
      'browser_navigate',
    ]

    // Platform-specific capabilities
    if (process.platform === 'darwin') {
      base.push('app_launch')
    }

    return base
  }

  /**
   * Register with pre-existing auth token (from device linking flow).
   */
  async registerWithToken(agentId: string, authToken: string): Promise<void> {
    console.log('[agent] Registering with pre-existing token...')

    try {
      // Set the credentials directly
      this.api.setAgentCredentials(agentId, authToken)

      this.updateState({
        status: 'registered',
        agentId: agentId,
      })

      console.log('[agent] Registered with token:', agentId)

      // Start heartbeat
      this.startHeartbeat()

    } catch (error) {
      console.error('[agent] Registration with token failed:', error)
      this.updateState({
        status: 'error',
        lastError: error instanceof Error ? error.message : 'Registration failed',
      })
      throw error
    }
  }

  /**
   * Register with the Sakhi API.
   */
  async register(personId: string, agentName?: string): Promise<void> {
    console.log('[agent] Registering...')

    try {
      this.api.setPersonId(personId)

      const response = await this.api.register({
        agent_name: agentName || `${process.platform} Agent`,
        agent_type: 'desktop',
        device_id: this.deviceId,
        agent_version: AGENT_VERSION,
        protocol_version: PROTOCOL_VERSION,
        capabilities: this.getCapabilities(),
        platform: process.platform === 'darwin' ? 'macos'
          : process.platform === 'win32' ? 'windows'
          : 'linux',
        platform_version: process.getSystemVersion(),
        architecture: process.arch,
      })

      this.updateState({
        status: 'registered',
        agentId: response.agent_id,
      })

      console.log('[agent] Registered successfully:', response.agent_id)

      // Check for pending approvals
      if (response.pending_approval.length > 0) {
        console.log('[agent] Pending capability approvals:', response.pending_approval)
      }

      // Check for updates
      if (response.update_available && response.latest_version) {
        console.log('[agent] Update available:', response.latest_version)
        const shouldUpdate = await promptForUpdate(response.latest_version)
        if (shouldUpdate) {
          await downloadUpdate()
          installUpdate()
        }
      }

      // Start heartbeat
      this.startHeartbeat()

    } catch (error) {
      console.error('[agent] Registration failed:', error)
      this.updateState({
        status: 'error',
        lastError: error instanceof Error ? error.message : 'Registration failed',
      })
      throw error
    }
  }

  /**
   * Start the heartbeat loop.
   */
  private startHeartbeat(): void {
    if (this.heartbeatInterval) return

    this.heartbeatInterval = setInterval(async () => {
      await this.sendHeartbeat()
    }, HEARTBEAT_INTERVAL_MS)

    // Send initial heartbeat
    this.sendHeartbeat()
  }

  /**
   * Send heartbeat to API.
   */
  private async sendHeartbeat(): Promise<void> {
    try {
      const response = await this.api.heartbeat(
        this.state.status === 'executing' ? 'busy' : 'online',
        this.state.sessionId || undefined
      )

      this.updateState({ lastHeartbeat: new Date() })

      // Check for pending actions
      if (response.has_pending_actions && this.state.status !== 'executing') {
        console.log('[agent] Pending actions:', response.pending_action_count)
        // Set status to active to allow action execution
        if (this.state.status === 'registered' || this.state.status === 'idle') {
          this.updateState({ status: 'active' })
        }
        this.startActionPolling()
      }

      // Check for mandatory updates
      if (response.update_mandatory && response.latest_version) {
        console.log('[agent] Mandatory update required:', response.latest_version)
        await downloadUpdate()
        installUpdate()
      }

      // Process commands
      for (const cmd of response.commands) {
        await this.handleCommand(cmd)
      }

    } catch (error) {
      console.error('[agent] Heartbeat failed:', error)
    }
  }

  /**
   * Handle a command from the API.
   */
  private async handleCommand(cmd: { command: string; parameters: Record<string, unknown> }): Promise<void> {
    console.log('[agent] Received command:', cmd.command, cmd.parameters)

    switch (cmd.command) {
      case 'start_session':
        // Check if an existing session_id was provided (from VisionLoop)
        const existingSessionId = cmd.parameters.session_id as string | undefined
        const taskDescription = cmd.parameters.task_description as string

        if (existingSessionId) {
          // Use existing session - just update state and capture screenshot
          console.log('[agent] Joining existing session:', existingSessionId)
          this.updateState({
            status: 'active',
            sessionId: existingSessionId,
            currentTask: taskDescription,
          })
          this.startActionPolling()
          // Capture initial screenshot for the session
          await this.captureAndSubmitScreen('session_start')
        } else {
          // Create new session via API (legacy flow)
          await this.startSession(taskDescription)
        }
        break

      case 'end_session':
        await this.endSession()
        break

      case 'pause_session':
        this.updateState({ status: 'paused' })
        break

      case 'resume_session':
        this.updateState({ status: 'active' })
        this.startActionPolling()
        break

      case 'take_screenshot':
        await this.captureAndSubmitScreen('api_request')
        break

      default:
        console.warn('[agent] Unknown command:', cmd.command)
    }
  }

  /**
   * Start a new task session.
   */
  async startSession(taskDescription: string): Promise<void> {
    console.log('[agent] Starting session:', taskDescription)

    try {
      const response = await this.api.startSession(taskDescription)

      this.updateState({
        status: 'active',
        sessionId: response.session_id,
        currentTask: taskDescription,
      })

      // Execute initial actions if any
      if (response.initial_actions.length > 0) {
        await this.executeActions(response.initial_actions)
      }

      // Start polling for more actions
      this.startActionPolling()

      // Capture initial screenshot
      await this.captureAndSubmitScreen('session_start')

    } catch (error) {
      console.error('[agent] Failed to start session:', error)
      this.updateState({
        lastError: error instanceof Error ? error.message : 'Session start failed',
      })
    }
  }

  /**
   * End the current session.
   */
  async endSession(status: string = 'completed'): Promise<void> {
    if (!this.state.sessionId) return

    console.log('[agent] Ending session:', status)

    try {
      await this.api.endSession(this.state.sessionId, status)
    } catch (error) {
      console.error('[agent] Failed to end session:', error)
    }

    this.stopActionPolling()
    this.updateState({
      status: 'registered',
      sessionId: null,
      currentTask: null,
    })
  }

  /**
   * Start polling for actions.
   */
  private startActionPolling(): void {
    if (this.actionPollInterval) return

    this.actionPollInterval = setInterval(async () => {
      await this.pollAndExecuteActions()
    }, ACTION_POLL_INTERVAL_MS)
  }

  /**
   * Stop polling for actions.
   */
  private stopActionPolling(): void {
    if (this.actionPollInterval) {
      clearInterval(this.actionPollInterval)
      this.actionPollInterval = null
    }
  }

  /**
   * Poll for pending actions and execute them.
   */
  private async pollAndExecuteActions(): Promise<void> {
    if (this.state.status !== 'active') return

    try {
      const actions = await this.api.getPendingActions(5)

      if (actions.length > 0) {
        console.log('[agent] Got', actions.length, 'actions to execute')
        await this.executeActions(actions)
      }
    } catch (error) {
      console.error('[agent] Action poll failed:', error)
    }
  }

  /**
   * Execute a batch of actions.
   */
  private async executeActions(actions: AgentAction[]): Promise<void> {
    this.updateState({ status: 'executing' })

    const results = await executeActionBatch(actions, async (result) => {
      // Report each result immediately
      try {
        await this.api.reportActionResult(result)

        // Capture screenshot after action
        if (result.success) {
          await this.captureAndSubmitScreen('action_result', result.action_id)
        }
      } catch (error) {
        console.error('[agent] Failed to report result:', error)
      }
    })

    const successCount = results.filter(r => r.success).length
    const failCount = results.length - successCount

    console.log(`[agent] Executed ${results.length} actions: ${successCount} success, ${failCount} failed`)

    this.updateState({
      status: 'active',
      actionsExecuted: this.state.actionsExecuted + successCount,
    })
  }

  /**
   * Capture screenshot and submit to API.
   */
  async captureAndSubmitScreen(
    trigger: string = 'user_request',
    precedingActionId?: string
  ): Promise<void> {
    try {
      const capture = await captureScreen({ format: 'jpeg' })
      const base64 = captureToBase64(capture)
      const activeWindow = getActiveWindow()

      const response = await this.api.submitScreenshot({
        agent_id: this.state.agentId!,
        session_id: this.state.sessionId || undefined,
        image_base64: base64,
        format: capture.format,
        width: capture.width,
        height: capture.height,
        trigger,
        preceding_action_id: precedingActionId,
        captured_at: new Date().toISOString(),
        current_app: activeWindow.app,
        current_window_title: activeWindow.title,
      })

      console.log('[agent] Screenshot submitted:', response.screenshot_id)

      if (response.analysis) {
        console.log('[agent] Screen analysis:', response.analysis.description?.substring(0, 100))
      }

    } catch (error) {
      console.error('[agent] Screenshot submission failed:', error)
    }
  }

  /**
   * Update agent state and notify listeners.
   */
  private updateState(updates: Partial<AgentState>): void {
    this.state = { ...this.state, ...updates }
    this.listeners.forEach(listener => listener(this.state))
  }

  /**
   * Add a state change listener.
   */
  addListener(listener: StateListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /**
   * Get current state.
   */
  getState(): AgentState {
    return { ...this.state }
  }

  /**
   * Stop the agent.
   */
  async stop(): Promise<void> {
    console.log('[agent] Stopping...')

    if (this.state.sessionId) {
      await this.endSession('cancelled')
    }

    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }

    this.stopActionPolling()
    this.updateState({ status: 'idle' })
  }

  /**
   * Check if agent is registered.
   */
  get isRegistered(): boolean {
    return this.api.isRegistered
  }
}

// Singleton instance
let agent: SakhiAgent | null = null

export function getAgent(): SakhiAgent {
  if (!agent) {
    agent = new SakhiAgent()
  }
  return agent
}

export function initAgent(): SakhiAgent {
  const instance = getAgent()

  // Initialize updater
  initUpdater()

  return instance
}

export default SakhiAgent
