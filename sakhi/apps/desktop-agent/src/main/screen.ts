/**
 * Screen Capture Module
 * ---------------------
 * Captures screenshots for the Sakhi API to analyze.
 */

import { screen, desktopCapturer, BrowserWindow } from 'electron'
import screenshot from 'screenshot-desktop'

export interface CaptureResult {
  buffer: Buffer
  width: number
  height: number
  format: 'png' | 'jpeg'
}

export interface ScreenInfo {
  id: string
  name: string
  bounds: {
    x: number
    y: number
    width: number
    height: number
  }
  isPrimary: boolean
}

/**
 * Get information about all available displays.
 */
export function getDisplays(): ScreenInfo[] {
  const displays = screen.getAllDisplays()
  const primary = screen.getPrimaryDisplay()

  return displays.map((display, index) => ({
    id: display.id.toString(),
    name: `Display ${index + 1}`,
    bounds: display.bounds,
    isPrimary: display.id === primary.id,
  }))
}

/**
 * Capture the entire screen or a specific region.
 */
export async function captureScreen(options?: {
  displayId?: string
  region?: { x: number; y: number; width: number; height: number }
  format?: 'png' | 'jpeg'
  quality?: number
}): Promise<CaptureResult> {
  const format = options?.format || 'png'

  try {
    // Use screenshot-desktop for cross-platform capture
    const imgBuffer = await screenshot({
      format: format === 'jpeg' ? 'jpg' : 'png',
      screen: options?.displayId ? parseInt(options.displayId) : undefined,
    })

    // Get display dimensions
    const display = options?.displayId
      ? screen.getAllDisplays().find(d => d.id.toString() === options.displayId)
      : screen.getPrimaryDisplay()

    const bounds = display?.bounds || { width: 1920, height: 1080 }

    return {
      buffer: imgBuffer,
      width: bounds.width,
      height: bounds.height,
      format,
    }
  } catch (error) {
    console.error('[screen] Capture failed, trying Electron method:', error)

    // Fallback to Electron's desktopCapturer
    return captureWithElectron(options)
  }
}

/**
 * Fallback capture using Electron's desktopCapturer.
 */
async function captureWithElectron(options?: {
  displayId?: string
  format?: 'png' | 'jpeg'
}): Promise<CaptureResult> {
  const sources = await desktopCapturer.getSources({
    types: ['screen'],
    thumbnailSize: { width: 1920, height: 1080 },
  })

  const source = options?.displayId
    ? sources.find(s => s.display_id === options.displayId)
    : sources[0]

  if (!source) {
    throw new Error('No screen source found')
  }

  const thumbnail = source.thumbnail
  const format = options?.format || 'png'

  const buffer = format === 'jpeg'
    ? thumbnail.toJPEG(85)
    : thumbnail.toPNG()

  return {
    buffer,
    width: thumbnail.getSize().width,
    height: thumbnail.getSize().height,
    format,
  }
}

/**
 * Capture a specific window by title.
 */
export async function captureWindow(titlePattern: string): Promise<CaptureResult | null> {
  const sources = await desktopCapturer.getSources({
    types: ['window'],
    thumbnailSize: { width: 1920, height: 1080 },
  })

  const pattern = new RegExp(titlePattern, 'i')
  const source = sources.find(s => pattern.test(s.name))

  if (!source) {
    console.log('[screen] Window not found:', titlePattern)
    return null
  }

  const thumbnail = source.thumbnail

  return {
    buffer: thumbnail.toPNG(),
    width: thumbnail.getSize().width,
    height: thumbnail.getSize().height,
    format: 'png',
  }
}

/**
 * Convert capture result to base64 for API submission.
 */
export function captureToBase64(capture: CaptureResult): string {
  return capture.buffer.toString('base64')
}

/**
 * Get the currently active window info (platform-specific).
 */
export function getActiveWindow(): { app?: string; title?: string } {
  // Note: This is a simplified version. For proper implementation,
  // you'd use platform-specific APIs or a library like 'active-win'
  const windows = BrowserWindow.getAllWindows()
  const focused = windows.find(w => w.isFocused())

  if (focused) {
    return {
      app: 'Sakhi Agent',
      title: focused.getTitle(),
    }
  }

  return {}
}

/**
 * Continuous screen capture for real-time monitoring.
 */
export class ScreenMonitor {
  private intervalId: NodeJS.Timeout | null = null
  private onCapture: (capture: CaptureResult) => void
  private intervalMs: number

  constructor(
    onCapture: (capture: CaptureResult) => void,
    intervalMs: number = 1000
  ) {
    this.onCapture = onCapture
    this.intervalMs = intervalMs
  }

  start(): void {
    if (this.intervalId) return

    this.intervalId = setInterval(async () => {
      try {
        const capture = await captureScreen({ format: 'jpeg', quality: 60 })
        this.onCapture(capture)
      } catch (error) {
        console.error('[screen] Monitor capture failed:', error)
      }
    }, this.intervalMs)

    console.log(`[screen] Monitor started (${this.intervalMs}ms interval)`)
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
      console.log('[screen] Monitor stopped')
    }
  }

  isRunning(): boolean {
    return this.intervalId !== null
  }
}

export default {
  getDisplays,
  captureScreen,
  captureWindow,
  captureToBase64,
  getActiveWindow,
  ScreenMonitor,
}
