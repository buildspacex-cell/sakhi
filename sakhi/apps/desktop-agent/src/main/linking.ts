/**
 * Device Linking
 * --------------
 * Handles the OAuth-style device linking flow.
 *
 * Flow:
 * 1. Agent requests a link code from API
 * 2. User opens browser and enters code (or clicks link)
 * 3. User confirms in browser while signed in to Sakhi
 * 4. Agent polls API until link is confirmed
 * 5. API returns auth token for the agent
 */

import { shell } from 'electron'
import Store from 'electron-store'
import { v4 as uuidv4 } from 'uuid'

const store = new Store()

// API base URL - default to localhost for development
// Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues
const API_URL = process.env.SAKHI_API_URL || 'http://127.0.0.1:8080'
const WEB_URL = process.env.SAKHI_WEB_URL || 'http://localhost:3000'

export interface LinkCodeResponse {
  success: boolean
  code?: string
  expires_at?: string
  error?: string
}

export interface LinkStatusResponse {
  linked: boolean
  agent_id?: string
  auth_token?: string
  person_id?: string
  userName?: string
  error?: string
}

export interface AuthStatus {
  authenticated: boolean
  agentId?: string
  personId?: string
  userName?: string
}

/**
 * Get device ID (or generate if first time).
 */
export function getDeviceId(): string {
  let deviceId = store.get('device_id') as string | undefined

  if (!deviceId) {
    deviceId = uuidv4()
    store.set('device_id', deviceId)
  }

  return deviceId
}

/**
 * Request a new link code from the API.
 */
export async function requestLinkCode(): Promise<LinkCodeResponse> {
  try {
    const deviceId = getDeviceId()
    const platform = process.platform
    const arch = process.arch

    const response = await fetch(`${API_URL}/api/v1/agent/link/request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        device_id: deviceId,
        platform,
        architecture: arch,
        agent_type: 'desktop',
        agent_name: getDefaultAgentName(),
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return {
        success: false,
        error: errorData.detail || `HTTP ${response.status}`,
      }
    }

    const data = await response.json()

    // Store the code temporarily
    store.set('pending_link_code', data.code)

    return {
      success: true,
      code: data.code,
      expires_at: data.expires_at,
    }
  } catch (error) {
    console.error('[linking] Failed to request link code:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Connection failed',
    }
  }
}

/**
 * Open the browser to the linking page.
 */
export async function openLinkPage(code: string): Promise<void> {
  const url = `${WEB_URL}/link?code=${code}`
  await shell.openExternal(url)
}

/**
 * Check if the link has been confirmed.
 */
export async function checkLinkStatus(code: string): Promise<LinkStatusResponse> {
  try {
    const deviceId = getDeviceId()

    const response = await fetch(`${API_URL}/api/v1/agent/link/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code,
        device_id: deviceId,
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return {
        linked: false,
        error: errorData.detail || `HTTP ${response.status}`,
      }
    }

    const data = await response.json()

    if (data.linked) {
      // Store the auth credentials
      store.set('auth', {
        agent_id: data.agent_id,
        auth_token: data.auth_token,
        person_id: data.person_id,
        user_name: data.user_name,
        linked_at: new Date().toISOString(),
      })

      // Clear the pending code
      store.delete('pending_link_code')
    }

    return {
      linked: data.linked,
      agent_id: data.agent_id,
      auth_token: data.auth_token,
      person_id: data.person_id,
      userName: data.user_name,
    }
  } catch (error) {
    console.error('[linking] Failed to check link status:', error)
    return {
      linked: false,
      error: error instanceof Error ? error.message : 'Connection failed',
    }
  }
}

/**
 * Get the current auth status.
 */
export function getAuthStatus(): AuthStatus {
  const auth = store.get('auth') as {
    agent_id?: string
    person_id?: string
    user_name?: string
  } | undefined

  if (!auth || !auth.agent_id) {
    return { authenticated: false }
  }

  return {
    authenticated: true,
    agentId: auth.agent_id,
    personId: auth.person_id,
    userName: auth.user_name,
  }
}

/**
 * Get stored auth credentials.
 */
export function getAuthCredentials(): { agentId: string; authToken: string } | null {
  const auth = store.get('auth') as {
    agent_id?: string
    auth_token?: string
  } | undefined

  if (!auth || !auth.agent_id || !auth.auth_token) {
    return null
  }

  return {
    agentId: auth.agent_id,
    authToken: auth.auth_token,
  }
}

/**
 * Clear auth credentials (logout).
 */
export function clearAuth(): void {
  store.delete('auth')
  store.delete('pending_link_code')
}

/**
 * Check if this is the first launch.
 */
export function isFirstLaunch(): boolean {
  return !store.has('onboarding_completed')
}

/**
 * Mark onboarding as completed.
 */
export function completeOnboarding(): void {
  store.set('onboarding_completed', true)
  store.set('onboarding_completed_at', new Date().toISOString())
}

/**
 * Get a default agent name based on the machine.
 */
function getDefaultAgentName(): string {
  const os = require('os')
  const hostname = os.hostname()

  // Clean up hostname for display
  const cleanName = hostname
    .replace('.local', '')
    .replace('.lan', '')
    .replace(/-/g, ' ')

  // Capitalize first letter of each word
  const formatted = cleanName
    .split(' ')
    .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')

  return `${formatted} Desktop`
}

export default {
  getDeviceId,
  requestLinkCode,
  openLinkPage,
  checkLinkStatus,
  getAuthStatus,
  getAuthCredentials,
  clearAuth,
  isFirstLaunch,
  completeOnboarding,
}
