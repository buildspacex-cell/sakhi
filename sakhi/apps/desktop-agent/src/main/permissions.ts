/**
 * Permissions Helper
 * ------------------
 * Handles checking and requesting system permissions on different platforms.
 * macOS requires Accessibility and Screen Recording permissions.
 */

import { systemPreferences, shell } from 'electron'

export interface PermissionStatus {
  accessibility: boolean
  screenRecording: boolean
  allGranted: boolean
}

/**
 * Check all required permissions.
 */
export function checkPermissions(): PermissionStatus {
  const accessibility = checkAccessibility()
  const screenRecording = checkScreenRecording()

  return {
    accessibility,
    screenRecording,
    allGranted: accessibility && screenRecording,
  }
}

/**
 * Check if accessibility permission is granted.
 */
export function checkAccessibility(): boolean {
  if (process.platform !== 'darwin') {
    // On Windows/Linux, accessibility doesn't require special permissions
    return true
  }

  return systemPreferences.isTrustedAccessibilityClient(false)
}

/**
 * Check if screen recording permission is granted.
 */
export function checkScreenRecording(): boolean {
  if (process.platform !== 'darwin') {
    // On Windows/Linux, screen recording doesn't require special permissions
    return true
  }

  // On macOS, check screen capture permission
  const status = systemPreferences.getMediaAccessStatus('screen')
  return status === 'granted'
}

/**
 * Request accessibility permission.
 * On macOS, this opens System Preferences to the Accessibility pane.
 */
export async function requestAccessibility(): Promise<boolean> {
  if (process.platform !== 'darwin') {
    return true
  }

  // Check with prompt - this will show the system dialog if not already trusted
  const trusted = systemPreferences.isTrustedAccessibilityClient(true)

  if (!trusted) {
    // Also open System Preferences for the user
    await shell.openExternal(
      'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
    )
  }

  return trusted
}

/**
 * Request screen recording permission.
 * On macOS, this opens System Preferences to the Screen Recording pane.
 */
export async function requestScreenRecording(): Promise<boolean> {
  if (process.platform !== 'darwin') {
    return true
  }

  // There's no API to request screen recording, just open preferences
  await shell.openExternal(
    'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'
  )

  return false // User needs to manually enable
}

/**
 * Open system preferences to security & privacy.
 */
export async function openSecurityPreferences(): Promise<void> {
  if (process.platform === 'darwin') {
    await shell.openExternal(
      'x-apple.systempreferences:com.apple.preference.security?Privacy'
    )
  } else if (process.platform === 'win32') {
    // Open Windows Settings
    await shell.openExternal('ms-settings:privacy')
  }
}

/**
 * Get a human-readable description of missing permissions.
 */
export function getMissingPermissionsMessage(): string | null {
  const status = checkPermissions()

  if (status.allGranted) {
    return null
  }

  const missing: string[] = []

  if (!status.accessibility) {
    missing.push('Accessibility (for clicking and typing)')
  }

  if (!status.screenRecording) {
    missing.push('Screen Recording (for seeing your screen)')
  }

  return `Sakhi Agent needs the following permissions to work:\n\n${missing.join('\n')}\n\nPlease grant these in System Preferences.`
}

export default {
  checkPermissions,
  checkAccessibility,
  checkScreenRecording,
  requestAccessibility,
  requestScreenRecording,
  openSecurityPreferences,
  getMissingPermissionsMessage,
}
