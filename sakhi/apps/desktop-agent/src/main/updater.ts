/**
 * Auto-Updater Module
 * -------------------
 * Handles seamless agent updates.
 */

import { autoUpdater, UpdateInfo as ElectronUpdateInfo, ProgressInfo } from 'electron-updater'
import { app, dialog, BrowserWindow } from 'electron'
import { getAPIClient, UpdateInfo } from './api'

let isCheckingForUpdate = false
let updateWindow: BrowserWindow | null = null

export interface UpdateStatus {
  checking: boolean
  available: boolean
  downloading: boolean
  downloaded: boolean
  progress: number
  version?: string
  error?: string
}

type UpdateListener = (status: UpdateStatus) => void
const listeners: Set<UpdateListener> = new Set()

let currentStatus: UpdateStatus = {
  checking: false,
  available: false,
  downloading: false,
  downloaded: false,
  progress: 0,
}

function notifyListeners(status: Partial<UpdateStatus>): void {
  currentStatus = { ...currentStatus, ...status }
  listeners.forEach(listener => listener(currentStatus))
}

/**
 * Initialize the auto-updater.
 */
export function initUpdater(): void {
  // Configure auto-updater
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  // Event handlers
  autoUpdater.on('checking-for-update', () => {
    console.log('[updater] Checking for update...')
    notifyListeners({ checking: true })
  })

  autoUpdater.on('update-available', (info: ElectronUpdateInfo) => {
    console.log('[updater] Update available:', info.version)
    notifyListeners({
      checking: false,
      available: true,
      version: info.version,
    })
  })

  autoUpdater.on('update-not-available', () => {
    console.log('[updater] No update available')
    notifyListeners({ checking: false, available: false })
  })

  autoUpdater.on('download-progress', (progress: ProgressInfo) => {
    console.log(`[updater] Download progress: ${progress.percent.toFixed(1)}%`)
    notifyListeners({
      downloading: true,
      progress: progress.percent,
    })
  })

  autoUpdater.on('update-downloaded', (info: ElectronUpdateInfo) => {
    console.log('[updater] Update downloaded:', info.version)
    notifyListeners({
      downloading: false,
      downloaded: true,
      progress: 100,
    })
  })

  autoUpdater.on('error', (error: Error) => {
    console.error('[updater] Error:', error.message)
    notifyListeners({
      checking: false,
      downloading: false,
      error: error.message,
    })
  })
}

/**
 * Check for updates using the Sakhi API.
 */
export async function checkForUpdate(): Promise<UpdateInfo | null> {
  if (isCheckingForUpdate) {
    console.log('[updater] Already checking for update')
    return null
  }

  isCheckingForUpdate = true
  notifyListeners({ checking: true })

  try {
    const api = getAPIClient()
    const platform = process.platform === 'darwin' ? 'macos'
      : process.platform === 'win32' ? 'windows'
      : 'linux'

    const updateInfo = await api.checkUpdate(
      platform,
      app.getVersion(),
      process.arch
    )

    notifyListeners({
      checking: false,
      available: updateInfo.has_update,
      version: updateInfo.latest_version || undefined,
    })

    if (updateInfo.has_update) {
      console.log('[updater] Update available:', updateInfo.latest_version)

      // If mandatory, force update
      if (updateInfo.is_mandatory) {
        console.log('[updater] Mandatory update - starting download')
        await downloadUpdate()
      }
    }

    return updateInfo
  } catch (error) {
    console.error('[updater] Check failed:', error)
    notifyListeners({
      checking: false,
      error: error instanceof Error ? error.message : 'Check failed',
    })
    return null
  } finally {
    isCheckingForUpdate = false
  }
}

/**
 * Download the update.
 */
export async function downloadUpdate(): Promise<void> {
  notifyListeners({ downloading: true, progress: 0 })

  try {
    await autoUpdater.downloadUpdate()
  } catch (error) {
    console.error('[updater] Download failed:', error)
    notifyListeners({
      downloading: false,
      error: error instanceof Error ? error.message : 'Download failed',
    })
  }
}

/**
 * Install the update and restart.
 */
export function installUpdate(): void {
  console.log('[updater] Installing update and restarting...')
  autoUpdater.quitAndInstall(false, true)
}

/**
 * Show update dialog to user.
 */
export async function promptForUpdate(version: string, mandatory: boolean = false): Promise<boolean> {
  const message = mandatory
    ? `A required update (v${version}) is available. The app will update and restart.`
    : `A new version (v${version}) is available. Would you like to update now?`

  const buttons = mandatory
    ? ['Update Now']
    : ['Update Now', 'Later']

  const result = await dialog.showMessageBox({
    type: 'info',
    title: 'Update Available',
    message: 'Sakhi Agent Update',
    detail: message,
    buttons,
    defaultId: 0,
    cancelId: mandatory ? -1 : 1,
  })

  return result.response === 0
}

/**
 * Show download progress window.
 */
export function showProgressWindow(): void {
  if (updateWindow) {
    updateWindow.focus()
    return
  }

  updateWindow = new BrowserWindow({
    width: 400,
    height: 150,
    resizable: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  })

  updateWindow.loadURL(`data:text/html;charset=utf-8,
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: #1a1a2e;
          color: white;
          padding: 20px;
          margin: 0;
          border-radius: 12px;
        }
        h3 { margin: 0 0 15px 0; font-weight: 500; }
        .progress-bar {
          background: #333;
          border-radius: 8px;
          height: 8px;
          overflow: hidden;
        }
        .progress-fill {
          background: linear-gradient(90deg, #6366f1, #8b5cf6);
          height: 100%;
          width: 0%;
          transition: width 0.3s ease;
        }
        .status { margin-top: 10px; font-size: 14px; opacity: 0.8; }
      </style>
    </head>
    <body>
      <h3>Updating Sakhi Agent...</h3>
      <div class="progress-bar">
        <div class="progress-fill" id="progress"></div>
      </div>
      <div class="status" id="status">Downloading update...</div>
    </body>
    </html>
  `)

  // Update progress
  const unsubscribe = addListener((status) => {
    if (updateWindow && !updateWindow.isDestroyed()) {
      updateWindow.webContents.executeJavaScript(`
        document.getElementById('progress').style.width = '${status.progress}%';
        document.getElementById('status').textContent = '${
          status.downloaded ? 'Ready to install...'
          : status.downloading ? 'Downloading: ' + status.progress.toFixed(0) + '%'
          : 'Preparing...'
        }';
      `)

      if (status.downloaded) {
        setTimeout(() => {
          if (updateWindow && !updateWindow.isDestroyed()) {
            updateWindow.close()
          }
        }, 1000)
      }
    }
  })

  updateWindow.on('closed', () => {
    updateWindow = null
    unsubscribe()
  })
}

/**
 * Add a listener for update status changes.
 */
export function addListener(listener: UpdateListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * Get current update status.
 */
export function getStatus(): UpdateStatus {
  return { ...currentStatus }
}

/**
 * Schedule periodic update checks.
 */
export function scheduleUpdateChecks(intervalHours: number = 6): NodeJS.Timeout {
  const intervalMs = intervalHours * 60 * 60 * 1000

  // Check immediately on startup
  setTimeout(() => checkForUpdate(), 5000)

  // Then check periodically
  return setInterval(() => checkForUpdate(), intervalMs)
}

export default {
  initUpdater,
  checkForUpdate,
  downloadUpdate,
  installUpdate,
  promptForUpdate,
  showProgressWindow,
  addListener,
  getStatus,
  scheduleUpdateChecks,
}
