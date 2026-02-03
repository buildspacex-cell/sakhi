/**
 * Action Executor
 * ---------------
 * Executes mouse, keyboard, and system actions on the local machine.
 * Uses @jitsi/robotjs for cross-platform input automation.
 */

import robot from '@jitsi/robotjs'
import { shell, clipboard } from 'electron'
import type { AgentAction, ActionResult } from './api'

// Configure robotjs
robot.setMouseDelay(100)
robot.setKeyboardDelay(50)

/**
 * Map of key names to robotjs key strings.
 */
const KEY_MAP: Record<string, string> = {
  // Modifiers
  cmd: 'command',
  command: 'command',
  ctrl: 'control',
  control: 'control',
  alt: 'alt',
  option: 'alt',
  shift: 'shift',
  meta: 'command',
  super: 'command',

  // Navigation
  enter: 'enter',
  return: 'enter',
  tab: 'tab',
  escape: 'escape',
  esc: 'escape',
  backspace: 'backspace',
  delete: 'delete',
  space: 'space',

  // Arrow keys
  up: 'up',
  down: 'down',
  left: 'left',
  right: 'right',

  // Function keys
  f1: 'f1',
  f2: 'f2',
  f3: 'f3',
  f4: 'f4',
  f5: 'f5',
  f6: 'f6',
  f7: 'f7',
  f8: 'f8',
  f9: 'f9',
  f10: 'f10',
  f11: 'f11',
  f12: 'f12',

  // Other
  home: 'home',
  end: 'end',
  pageup: 'pageup',
  pagedown: 'pagedown',
  insert: 'insert',
}

/**
 * Parse a key string to robotjs key.
 */
function parseKey(keyStr: string): string {
  const normalized = keyStr.toLowerCase().trim()
  const mapped = KEY_MAP[normalized]

  if (mapped) return mapped

  // Single character - use as literal
  if (keyStr.length === 1) {
    return keyStr.toLowerCase()
  }

  console.warn(`[actions] Unknown key: ${keyStr}, defaulting to space`)
  return 'space'
}

/**
 * Execute a single action.
 */
export async function executeAction(action: AgentAction): Promise<ActionResult> {
  const startedAt = new Date().toISOString()
  const startTime = Date.now()

  try {
    const data = await performAction(action)

    const completedAt = new Date().toISOString()
    const durationMs = Date.now() - startTime

    return {
      action_id: action.action_id,
      success: true,
      started_at: startedAt,
      completed_at: completedAt,
      duration_ms: durationMs,
      data: data || {},
    }
  } catch (error) {
    const completedAt = new Date().toISOString()
    const durationMs = Date.now() - startTime

    return {
      action_id: action.action_id,
      success: false,
      error: error instanceof Error ? error.message : String(error),
      started_at: startedAt,
      completed_at: completedAt,
      duration_ms: durationMs,
      data: {},
    }
  }
}

/**
 * Perform the actual action.
 */
async function performAction(action: AgentAction): Promise<Record<string, unknown>> {
  const { action_type, parameters } = action

  console.log(`[actions] Executing: ${action_type}`, parameters)

  switch (action_type) {
    // ==========================================================
    // MOUSE ACTIONS
    // ==========================================================
    case 'click': {
      const x = parameters.x as number
      const y = parameters.y as number
      const button = (parameters.button as string) || 'left'

      robot.moveMouse(x, y)
      robot.mouseClick(button)

      return { clicked_at: { x, y }, button }
    }

    case 'double_click': {
      const x = parameters.x as number
      const y = parameters.y as number

      robot.moveMouse(x, y)
      robot.mouseClick('left', true) // double click

      return { clicked_at: { x, y } }
    }

    case 'right_click': {
      const x = parameters.x as number
      const y = parameters.y as number

      robot.moveMouse(x, y)
      robot.mouseClick('right')

      return { clicked_at: { x, y } }
    }

    case 'move_mouse': {
      const x = parameters.x as number
      const y = parameters.y as number

      robot.moveMouse(x, y)

      return { moved_to: { x, y } }
    }

    case 'drag': {
      const fromX = parameters.from_x as number
      const fromY = parameters.from_y as number
      const toX = parameters.to_x as number
      const toY = parameters.to_y as number

      robot.moveMouse(fromX, fromY)
      robot.mouseToggle('down')
      robot.moveMouse(toX, toY)
      robot.mouseToggle('up')

      return { dragged: { from: { x: fromX, y: fromY }, to: { x: toX, y: toY } } }
    }

    // ==========================================================
    // KEYBOARD ACTIONS
    // ==========================================================
    case 'type': {
      const text = parameters.text as string
      const delayMs = (parameters.delay_ms as number) || 50

      robot.setKeyboardDelay(delayMs)
      robot.typeString(text)

      return { typed: text.substring(0, 50), length: text.length }
    }

    case 'key': {
      const key = parameters.key as string
      const parsedKey = parseKey(key)

      robot.keyTap(parsedKey)

      return { key_pressed: key }
    }

    case 'shortcut': {
      const keys = parameters.keys as string[]

      // robotjs uses keyTap with modifiers as second argument
      const modifiers: string[] = []
      let mainKey = ''

      for (const key of keys) {
        const parsed = parseKey(key)
        if (['command', 'control', 'alt', 'shift'].includes(parsed)) {
          modifiers.push(parsed)
        } else {
          mainKey = parsed
        }
      }

      if (mainKey) {
        robot.keyTap(mainKey, modifiers)
      }

      return { shortcut: keys.join('+') }
    }

    // ==========================================================
    // SCROLL ACTIONS
    // ==========================================================
    case 'scroll': {
      const direction = (parameters.direction as string) || 'down'
      const amount = (parameters.amount as number) || 3

      // robotjs scrollMouse takes x, y for horizontal and vertical
      const scrollY = direction === 'up' ? amount : -amount
      robot.scrollMouse(0, scrollY)

      return { scrolled: direction, amount }
    }

    // ==========================================================
    // SYSTEM ACTIONS
    // ==========================================================
    case 'launch_app': {
      const appName = parameters.app_name as string

      // Platform-specific app launch
      if (process.platform === 'darwin') {
        await shell.openPath(`/Applications/${appName}.app`)
      } else if (process.platform === 'win32') {
        await shell.openPath(appName)
      } else {
        // Linux - try common paths
        await shell.openPath(`/usr/bin/${appName.toLowerCase()}`)
      }

      // Wait for app to launch
      await sleep(1000)

      return { launched: appName }
    }

    case 'navigate': {
      const url = parameters.url as string

      await shell.openExternal(url)

      // Wait for browser to open
      await sleep(1500)

      return { navigated_to: url }
    }

    // ==========================================================
    // CLIPBOARD ACTIONS
    // ==========================================================
    case 'copy': {
      // Trigger Cmd+C / Ctrl+C
      const modifier = process.platform === 'darwin' ? 'command' : 'control'

      robot.keyTap('c', modifier)

      // Wait for clipboard to update
      await sleep(100)

      const content = clipboard.readText()
      return { copied: content.substring(0, 100), length: content.length }
    }

    case 'paste': {
      // Trigger Cmd+V / Ctrl+V
      const modifier = process.platform === 'darwin' ? 'command' : 'control'

      robot.keyTap('v', modifier)

      return { pasted: true }
    }

    // ==========================================================
    // FLOW CONTROL
    // ==========================================================
    case 'wait': {
      const ms = (parameters.ms as number) || 1000
      await sleep(ms)
      return { waited_ms: ms }
    }

    case 'screenshot': {
      // Screenshot is handled separately
      return { note: 'Screenshot should be captured by screen module' }
    }

    default:
      throw new Error(`Unknown action type: ${action_type}`)
  }
}

/**
 * Execute a batch of actions sequentially.
 */
export async function executeActionBatch(
  actions: AgentAction[],
  onResult?: (result: ActionResult) => void
): Promise<ActionResult[]> {
  const results: ActionResult[] = []

  for (const action of actions) {
    const result = await executeAction(action)
    results.push(result)

    if (onResult) {
      onResult(result)
    }

    // Stop on failure unless retry is configured
    if (!result.success && !action.retry_on_fail) {
      console.warn(`[actions] Action failed, stopping batch: ${result.error}`)
      break
    }
  }

  return results
}

/**
 * Helper to sleep for a duration.
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Get current mouse position.
 */
export function getMousePosition(): { x: number; y: number } {
  return robot.getMousePos()
}

/**
 * Check if a point is within screen bounds.
 */
export function isValidPoint(x: number, y: number): boolean {
  const screenSize = robot.getScreenSize()
  return x >= 0 && y >= 0 && x < screenSize.width && y < screenSize.height
}

/**
 * Get screen size.
 */
export function getScreenSize(): { width: number; height: number } {
  return robot.getScreenSize()
}

export default {
  executeAction,
  executeActionBatch,
  getMousePosition,
  isValidPoint,
  getScreenSize,
}
