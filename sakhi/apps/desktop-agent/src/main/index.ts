/**
 * Sakhi Desktop Agent - Main Entry Point
 * ---------------------------------------
 * Electron main process with tray icon, onboarding, and minimal UI.
 */

import {
  app,
  BrowserWindow,
  Tray,
  Menu,
  nativeImage,
  ipcMain,
  shell,
} from 'electron'
import { join } from 'path'
import { initAgent, getAgent, AgentState } from './agent'
import { scheduleUpdateChecks, checkForUpdate } from './updater'
import {
  checkPermissions,
  requestAccessibility,
  requestScreenRecording,
} from './permissions'
import {
  getAuthStatus,
  requestLinkCode,
  openLinkPage,
  checkLinkStatus,
  isFirstLaunch,
  completeOnboarding,
  getAuthCredentials,
} from './linking'

let tray: Tray | null = null
let mainWindow: BrowserWindow | null = null
let onboardingWindow: BrowserWindow | null = null
let isQuitting = false

// App configuration
const APP_NAME = 'Sakhi Agent'
const WEB_APP_URL = process.env.SAKHI_WEB_URL || 'https://sakhi.ai'

/**
 * Create the tray icon.
 */
function createTray(): void {
  // Create tray icon (use a simple circle for now)
  const icon = nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAAsTAAALEwEAmpwYAAABhElEQVR4nO2WTU7DMBCFP1BYsOACLDkBS5YcgQ0n4AYcIXfo/ZZIPQOCJYtSCSTaOp7xJG7qRI1U2bFnvs/z4pmiKOp/C8BZYgMC8hS4AS4j9HXgHHgD3oC36F7tAFwCR4kN3ABfwJnhOAf2gQ/gtSjK4g44kGw6AvCpAM9D7gG4AKYZ7SzwCbx0aDkHPgAvwFvIVUCuOAceAM+G47wCM5h3xIEfwL3h+B7IC/k1lBdxoEsATwIcO5G/Ad8JnSXAMXC1w31pgHX7M2ABPAY+a09QK3Rp6UCtAHfEviYBeAU+hvcpzHwEPrQCSEMqBnCz87/hfFYA3WLXCoA8p5QCYBZw7nCM4Dt5bTwm7IqWYQpMYlj7RvlK+QI+a/lHC+D+A7CIKnTT8TzW7C9TKkYBeM5olXnsgR+YrgVg5nFjTd7sPPazlkJpANaCo8R+ow+AuxRr/wJmCdYGYO3E3d6bWQ/AzNqlH4BpyJVAGkDNTpwbvQ5ICL3+v/AP8rQf+RFa5QAAAABJRU5ErkJggg=='
  )

  tray = new Tray(icon)
  tray.setToolTip(APP_NAME)

  updateTrayMenu()

  // Click on tray icon shows window
  tray.on('click', () => {
    const auth = getAuthStatus()
    if (!auth.authenticated) {
      showOnboarding()
    } else if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show()
    } else {
      createMainWindow()
    }
  })
}

/**
 * Update the tray context menu based on agent state.
 */
function updateTrayMenu(): void {
  if (!tray) return

  const auth = getAuthStatus()
  const agent = getAgent()
  const state = agent?.getState() || { status: 'idle' }

  const menuItems: Electron.MenuItemConstructorOptions[] = [
    {
      label: APP_NAME,
      enabled: false,
    },
    { type: 'separator' },
  ]

  if (auth.authenticated) {
    menuItems.push(
      {
        label: `Signed in as ${auth.userName || 'User'}`,
        enabled: false,
      },
      {
        label: getStatusLabel(state as AgentState),
        enabled: false,
      },
      { type: 'separator' },
      {
        label: 'Open Dashboard',
        click: () => {
          if (mainWindow) {
            mainWindow.show()
          } else {
            createMainWindow()
          }
        },
      },
      {
        label: 'Open Sakhi',
        click: () => {
          shell.openExternal(WEB_APP_URL)
        },
      },
      { type: 'separator' },
      {
        label: 'Check for Updates',
        click: async () => {
          await checkForUpdate()
        },
      },
      {
        label: 'Sign Out',
        click: () => {
          const { clearAuth } = require('./linking')
          clearAuth()
          updateTrayMenu()
          showOnboarding()
        },
      }
    )
  } else {
    menuItems.push(
      {
        label: 'Not signed in',
        enabled: false,
      },
      { type: 'separator' },
      {
        label: 'Sign In to Sakhi',
        click: () => {
          showOnboarding()
        },
      }
    )
  }

  menuItems.push(
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true
        app.quit()
      },
    }
  )

  const contextMenu = Menu.buildFromTemplate(menuItems)
  tray.setContextMenu(contextMenu)
}

/**
 * Get status label for tray menu.
 */
function getStatusLabel(state: AgentState): string {
  switch (state.status) {
    case 'idle':
      return '○ Idle'
    case 'registered':
      return '● Connected'
    case 'active':
      return `● Active: ${state.currentTask?.substring(0, 30) || 'Working...'}`
    case 'executing':
      return '◉ Executing...'
    case 'paused':
      return '◐ Paused'
    case 'error':
      return `✕ Error: ${state.lastError?.substring(0, 30) || 'Unknown'}`
    default:
      return '○ Ready'
  }
}

/**
 * Show the onboarding window.
 */
function showOnboarding(): void {
  if (onboardingWindow) {
    onboardingWindow.show()
    onboardingWindow.focus()
    return
  }

  onboardingWindow = new BrowserWindow({
    width: 560,
    height: 700,
    minWidth: 480,
    minHeight: 600,
    show: false,
    frame: false,
    titleBarStyle: 'hiddenInset',
    vibrancy: 'window',
    backgroundColor: '#ffffff',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Load onboarding page
  if (process.env.NODE_ENV === 'development') {
    // In dev mode, load from vite dev server
    const devServerPort = process.env.ELECTRON_RENDERER_URL?.match(/:(\d+)/)?.[1] || '5173'
    onboardingWindow.loadURL(`http://localhost:${devServerPort}/onboarding.html`)
    onboardingWindow.webContents.openDevTools()
  } else {
    onboardingWindow.loadFile(join(__dirname, '../renderer/onboarding.html'))
  }

  onboardingWindow.on('ready-to-show', () => {
    onboardingWindow?.show()
  })

  onboardingWindow.on('closed', () => {
    onboardingWindow = null
  })
}

/**
 * Create the main dashboard window.
 */
function createMainWindow(): void {
  mainWindow = new BrowserWindow({
    width: 480,
    height: 600,
    minWidth: 400,
    minHeight: 400,
    show: false,
    frame: false,
    titleBarStyle: 'hiddenInset',
    vibrancy: 'sidebar',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Load renderer
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  // Hide instead of close (keep in tray)
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow?.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

/**
 * Setup IPC handlers for renderer communication.
 */
function setupIPC(): void {
  // ==========================================================================
  // AUTH / LINKING
  // ==========================================================================

  ipcMain.handle('auth:getStatus', () => {
    return getAuthStatus()
  })

  ipcMain.handle('auth:requestLinkCode', async () => {
    return await requestLinkCode()
  })

  ipcMain.handle('auth:openLinkPage', async (_event, code: string) => {
    await openLinkPage(code)
  })

  ipcMain.handle('auth:checkLinkStatus', async (_event, code: string) => {
    const result = await checkLinkStatus(code)

    // If linked successfully, update tray and potentially auto-register agent
    if (result.linked) {
      updateTrayMenu()

      // Auto-register the agent
      const agent = getAgent()
      const creds = getAuthCredentials()
      if (agent && creds) {
        try {
          await agent.registerWithToken(creds.agentId, creds.authToken)
        } catch (error) {
          console.error('[ipc] Failed to auto-register agent:', error)
        }
      }
    }

    return result
  })

  // ==========================================================================
  // PERMISSIONS
  // ==========================================================================

  ipcMain.handle('permissions:check', () => {
    return checkPermissions()
  })

  ipcMain.handle('permissions:requestAccessibility', async () => {
    return await requestAccessibility()
  })

  ipcMain.handle('permissions:requestScreenRecording', async () => {
    return await requestScreenRecording()
  })

  // ==========================================================================
  // ONBOARDING
  // ==========================================================================

  ipcMain.handle('onboarding:finish', () => {
    completeOnboarding()
    updateTrayMenu()

    // Close onboarding window
    if (onboardingWindow) {
      onboardingWindow.close()
      onboardingWindow = null
    }
  })

  ipcMain.handle('onboarding:openApp', async () => {
    await shell.openExternal(WEB_APP_URL)
  })

  // ==========================================================================
  // WINDOW CONTROLS
  // ==========================================================================

  ipcMain.handle('window:close', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win) {
      win.close()
    }
  })

  ipcMain.on('window:minimize', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win) {
      win.minimize()
    }
  })

  ipcMain.on('window:close', () => {
    const win = BrowserWindow.getFocusedWindow()
    if (win) {
      win.close()
    }
  })

  // ==========================================================================
  // AGENT
  // ==========================================================================

  const agent = getAgent()

  ipcMain.handle('agent:getState', () => {
    return agent?.getState() || { status: 'idle' }
  })

  ipcMain.handle('agent:register', async (_event, personId: string, agentName?: string) => {
    if (!agent) return { status: 'error', lastError: 'Agent not initialized' }
    await agent.register(personId, agentName)
    updateTrayMenu()
    return agent.getState()
  })

  ipcMain.handle('agent:startTask', async (_event, taskDescription: string) => {
    if (!agent) return { status: 'error', lastError: 'Agent not initialized' }
    await agent.startSession(taskDescription)
    updateTrayMenu()
    return agent.getState()
  })

  ipcMain.handle('agent:stopTask', async () => {
    if (!agent) return { status: 'error', lastError: 'Agent not initialized' }
    await agent.endSession('cancelled')
    updateTrayMenu()
    return agent.getState()
  })

  ipcMain.handle('agent:screenshot', async () => {
    if (!agent) return { success: false }
    await agent.captureAndSubmitScreen('user_request')
    return { success: true }
  })

  // State changes - broadcast to all windows
  agent?.addListener((state: AgentState) => {
    updateTrayMenu()
    mainWindow?.webContents.send('agent:stateChanged', state)
  })
}

/**
 * Initialize the application.
 */
async function init(): Promise<void> {
  // Single instance lock
  const gotLock = app.requestSingleInstanceLock()
  if (!gotLock) {
    app.quit()
    return
  }

  app.on('second-instance', () => {
    const auth = getAuthStatus()
    if (!auth.authenticated && onboardingWindow) {
      onboardingWindow.show()
      onboardingWindow.focus()
    } else if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })

  // App event handlers
  app.on('ready', async () => {
    console.log('[app] Sakhi Agent starting...')

    // Initialize agent
    initAgent()

    // Create tray
    createTray()

    // Setup IPC
    setupIPC()

    // Check if first launch or not authenticated
    const auth = getAuthStatus()
    if (isFirstLaunch() || !auth.authenticated) {
      console.log('[app] First launch or not authenticated, showing onboarding')
      showOnboarding()
    } else {
      console.log('[app] Already authenticated, starting in background')

      // Auto-register with stored credentials
      const agent = getAgent()
      const creds = getAuthCredentials()
      if (agent && creds) {
        try {
          await agent.registerWithToken(creds.agentId, creds.authToken)
          console.log('[app] Agent registered successfully')
        } catch (error) {
          console.error('[app] Failed to register agent:', error)
        }
      }
    }

    // Schedule update checks
    scheduleUpdateChecks(6) // Every 6 hours

    console.log('[app] Sakhi Agent started')
  })

  app.on('window-all-closed', () => {
    // Keep running in tray on all platforms
    // Don't quit here
  })

  app.on('activate', () => {
    const auth = getAuthStatus()
    if (!auth.authenticated) {
      showOnboarding()
    } else if (mainWindow === null) {
      createMainWindow()
    }
  })

  app.on('before-quit', () => {
    isQuitting = true
  })
}

// Start the application
init()
