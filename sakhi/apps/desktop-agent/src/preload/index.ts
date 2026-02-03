/**
 * Preload Script
 * --------------
 * Exposes safe APIs to the renderer process.
 */

import { contextBridge, ipcRenderer } from 'electron'

// Types for the exposed API
export interface AgentState {
  status: 'idle' | 'registered' | 'active' | 'executing' | 'paused' | 'error'
  agentId: string | null
  sessionId: string | null
  currentTask: string | null
  lastHeartbeat: Date | null
  actionsExecuted: number
  lastError: string | null
}

export interface PermissionStatus {
  accessibility: boolean
  screenRecording: boolean
  allGranted: boolean
}

export interface AuthStatus {
  authenticated: boolean
  agentId?: string
  personId?: string
  userName?: string
}

export interface LinkCodeResult {
  success: boolean
  code?: string
  error?: string
}

export interface LinkStatusResult {
  linked: boolean
  userName?: string
  error?: string
}

export interface SakhiAPI {
  // Agent control
  getState: () => Promise<AgentState>
  register: (personId: string, agentName?: string) => Promise<AgentState>
  startTask: (taskDescription: string) => Promise<AgentState>
  stopTask: () => Promise<AgentState>
  screenshot: () => Promise<{ success: boolean }>

  // Event listeners
  onStateChange: (callback: (state: AgentState) => void) => () => void

  // App info
  getVersion: () => string
  getPlatform: () => string

  // Window controls
  minimize: () => void
  close: () => void
}

export interface ElectronAPI {
  // Auth / Linking
  getAuthStatus: () => Promise<AuthStatus>
  requestLinkCode: () => Promise<LinkCodeResult>
  openLinkPage: (code: string) => Promise<void>
  checkLinkStatus: (code: string) => Promise<LinkStatusResult>

  // Permissions
  getPermissions: () => Promise<PermissionStatus>
  requestAccessibility: () => Promise<boolean>
  requestScreenRecording: () => Promise<boolean>

  // Onboarding
  finishOnboarding: () => Promise<void>
  openSakhiApp: () => Promise<void>
  closeWindow: () => Promise<void>
}

// Expose the main agent API
contextBridge.exposeInMainWorld('sakhi', {
  // Agent control
  getState: () => ipcRenderer.invoke('agent:getState'),
  register: (personId: string, agentName?: string) =>
    ipcRenderer.invoke('agent:register', personId, agentName),
  startTask: (taskDescription: string) =>
    ipcRenderer.invoke('agent:startTask', taskDescription),
  stopTask: () => ipcRenderer.invoke('agent:stopTask'),
  screenshot: () => ipcRenderer.invoke('agent:screenshot'),

  // Event listeners
  onStateChange: (callback: (state: AgentState) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, state: AgentState) => {
      callback(state)
    }
    ipcRenderer.on('agent:stateChanged', listener)
    return () => ipcRenderer.removeListener('agent:stateChanged', listener)
  },

  // App info
  getVersion: () => process.env.npm_package_version || '1.0.0',
  getPlatform: () => process.platform,

  // Window controls
  minimize: () => ipcRenderer.send('window:minimize'),
  close: () => ipcRenderer.send('window:close'),
} as SakhiAPI)

// Expose the onboarding/electron API
contextBridge.exposeInMainWorld('electronAPI', {
  // Auth / Linking
  getAuthStatus: () => ipcRenderer.invoke('auth:getStatus'),
  requestLinkCode: () => ipcRenderer.invoke('auth:requestLinkCode'),
  openLinkPage: (code: string) => ipcRenderer.invoke('auth:openLinkPage', code),
  checkLinkStatus: (code: string) => ipcRenderer.invoke('auth:checkLinkStatus', code),

  // Permissions
  getPermissions: () => ipcRenderer.invoke('permissions:check'),
  requestAccessibility: () => ipcRenderer.invoke('permissions:requestAccessibility'),
  requestScreenRecording: () => ipcRenderer.invoke('permissions:requestScreenRecording'),

  // Onboarding
  finishOnboarding: () => ipcRenderer.invoke('onboarding:finish'),
  openSakhiApp: () => ipcRenderer.invoke('onboarding:openApp'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
} as ElectronAPI)

// Type declaration for window object
declare global {
  interface Window {
    sakhi: SakhiAPI
    electronAPI: ElectronAPI
  }
}
