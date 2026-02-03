/**
 * Sakhi Agent Onboarding
 * ----------------------
 * Handles the multi-step onboarding flow for new users.
 */

// Current step (1-4)
let currentStep = 1
let linkCode = null
let linkPollInterval = null
let codeExpiryInterval = null
let codeExpiryTime = 600 // 10 minutes in seconds
let permissionPollInterval = null

// Access the Electron API exposed via preload
const api = window.electronAPI

/**
 * Navigate to the next step.
 */
function nextStep() {
  if (currentStep < 4) {
    setStep(currentStep + 1)
  }
}

/**
 * Navigate to a specific step.
 */
function setStep(step) {
  // Update step indicators
  document.querySelectorAll('.step').forEach((el, index) => {
    el.classList.remove('active', 'completed')
    if (index + 1 < step) {
      el.classList.add('completed')
    } else if (index + 1 === step) {
      el.classList.add('active')
    }
  })

  // Update screens
  document.querySelectorAll('.screen').forEach((el) => {
    el.classList.remove('active')
  })

  const screens = ['screen-welcome', 'screen-signin', 'screen-permissions', 'screen-ready']
  document.getElementById(screens[step - 1]).classList.add('active')

  currentStep = step

  // Trigger step-specific logic
  if (step === 3) {
    checkPermissions()
    startPermissionPolling()
  } else {
    stopPermissionPolling()
  }
}

// =============================================================================
// SIGN IN / DEVICE LINKING
// =============================================================================

/**
 * Start the device linking process.
 */
async function startLinking() {
  try {
    // Request a link code from the API
    const result = await api.requestLinkCode()

    if (result.success) {
      linkCode = result.code
      showLinkingUI(result.code)

      // Open browser to linking page
      await api.openLinkPage(result.code)

      // Start polling for confirmation
      startLinkPolling()
    } else {
      showSignInError(result.error || 'Failed to get link code')
    }
  } catch (error) {
    showSignInError(error.message || 'Connection failed')
  }
}

/**
 * Show the linking UI with the code.
 */
function showLinkingUI(code) {
  document.getElementById('signin-initial').classList.add('hidden')
  document.getElementById('signin-waiting').classList.remove('hidden')
  document.getElementById('signin-success').classList.add('hidden')
  document.getElementById('signin-error').classList.add('hidden')

  // Format code as XXXX-XXXX
  const formatted = code.slice(0, 4) + '-' + code.slice(4)
  document.getElementById('link-code').textContent = formatted

  // Start expiry countdown
  codeExpiryTime = 600
  updateExpiryDisplay()
  codeExpiryInterval = setInterval(() => {
    codeExpiryTime--
    updateExpiryDisplay()
    if (codeExpiryTime <= 0) {
      cancelLinking()
      showSignInError('Code expired. Please try again.')
    }
  }, 1000)
}

/**
 * Update the expiry time display.
 */
function updateExpiryDisplay() {
  const minutes = Math.floor(codeExpiryTime / 60)
  const seconds = codeExpiryTime % 60
  document.getElementById('code-expiry').textContent =
    `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * Start polling the API to check if linking is complete.
 */
function startLinkPolling() {
  linkPollInterval = setInterval(async () => {
    try {
      const result = await api.checkLinkStatus(linkCode)

      if (result.linked) {
        stopLinkPolling()
        showSignInSuccess(result.userName)
      }
    } catch (error) {
      console.error('Link poll error:', error)
    }
  }, 2000) // Poll every 2 seconds
}

/**
 * Stop polling for link status.
 */
function stopLinkPolling() {
  if (linkPollInterval) {
    clearInterval(linkPollInterval)
    linkPollInterval = null
  }
  if (codeExpiryInterval) {
    clearInterval(codeExpiryInterval)
    codeExpiryInterval = null
  }
}

/**
 * Cancel the linking process.
 */
function cancelLinking() {
  stopLinkPolling()
  linkCode = null

  document.getElementById('signin-initial').classList.remove('hidden')
  document.getElementById('signin-waiting').classList.add('hidden')
}

/**
 * Retry linking after an error.
 */
function retryLinking() {
  document.getElementById('signin-initial').classList.remove('hidden')
  document.getElementById('signin-error').classList.add('hidden')
}

/**
 * Show sign in success.
 */
function showSignInSuccess(userName) {
  document.getElementById('signin-initial').classList.add('hidden')
  document.getElementById('signin-waiting').classList.add('hidden')
  document.getElementById('signin-error').classList.add('hidden')
  document.getElementById('signin-success').classList.remove('hidden')

  document.getElementById('user-name').textContent = userName || 'User'
}

/**
 * Show sign in error.
 */
function showSignInError(message) {
  document.getElementById('signin-initial').classList.add('hidden')
  document.getElementById('signin-waiting').classList.add('hidden')
  document.getElementById('signin-success').classList.add('hidden')
  document.getElementById('signin-error').classList.remove('hidden')

  document.getElementById('error-message').textContent = message
}

// =============================================================================
// PERMISSIONS
// =============================================================================

/**
 * Start polling for permission changes.
 */
function startPermissionPolling() {
  if (permissionPollInterval) return

  console.log('[onboarding] Starting permission polling')
  permissionPollInterval = setInterval(async () => {
    await checkPermissions()
  }, 2000) // Check every 2 seconds
}

/**
 * Stop polling for permission changes.
 */
function stopPermissionPolling() {
  if (permissionPollInterval) {
    console.log('[onboarding] Stopping permission polling')
    clearInterval(permissionPollInterval)
    permissionPollInterval = null
  }
}

/**
 * Check current permission status.
 */
async function checkPermissions() {
  try {
    const permissions = await api.getPermissions()

    updatePermissionUI('accessibility', permissions.accessibility)
    updatePermissionUI('screen', permissions.screenRecording)

    // Enable continue button if both are granted
    const continueBtn = document.getElementById('btn-continue-permissions')
    if (permissions.accessibility && permissions.screenRecording) {
      continueBtn.disabled = false
      // Stop polling once both are granted
      stopPermissionPolling()
    }
  } catch (error) {
    console.error('Failed to check permissions:', error)
  }
}

/**
 * Update the UI for a permission.
 */
function updatePermissionUI(permission, granted) {
  const statusEl = document.getElementById(`status-${permission}`)
  const itemEl = document.getElementById(`perm-${permission}`)

  if (granted) {
    statusEl.innerHTML = '<span class="status-granted">✓</span>'
    itemEl.querySelector('.btn-small').textContent = 'Granted'
    itemEl.querySelector('.btn-small').disabled = true
  } else {
    statusEl.innerHTML = '<span class="status-pending">○</span>'
    itemEl.querySelector('.btn-small').textContent = 'Grant'
    itemEl.querySelector('.btn-small').disabled = false
  }
}

/**
 * Request accessibility permission.
 */
async function requestAccessibility() {
  try {
    await api.requestAccessibility()
    // Re-check after a delay (user may need to enable in System Preferences)
    setTimeout(checkPermissions, 1000)
  } catch (error) {
    console.error('Failed to request accessibility:', error)
  }
}

/**
 * Request screen recording permission.
 */
async function requestScreenRecording() {
  try {
    await api.requestScreenRecording()
    // Re-check after a delay
    setTimeout(checkPermissions, 1000)
  } catch (error) {
    console.error('Failed to request screen recording:', error)
  }
}

/**
 * Skip permissions for now.
 */
function skipPermissions() {
  nextStep()
}

// =============================================================================
// FINISH
// =============================================================================

/**
 * Finish onboarding and open Sakhi app.
 */
async function finishOnboarding() {
  try {
    await api.finishOnboarding()
    await api.openSakhiApp()
  } catch (error) {
    console.error('Failed to finish onboarding:', error)
  }
}

/**
 * Close the onboarding window.
 */
async function closeOnboarding() {
  try {
    await api.finishOnboarding()
    await api.closeWindow()
  } catch (error) {
    console.error('Failed to close onboarding:', error)
  }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('[onboarding] Initialized')

  // Check if already signed in
  try {
    const status = await api.getAuthStatus()
    if (status.authenticated) {
      // Skip to permissions
      setStep(3)
    }
  } catch (error) {
    console.log('[onboarding] Not authenticated, starting from beginning')
  }
})

// Export functions to window for onclick handlers
window.nextStep = nextStep
window.startLinking = startLinking
window.cancelLinking = cancelLinking
window.retryLinking = retryLinking
window.requestAccessibility = requestAccessibility
window.requestScreenRecording = requestScreenRecording
window.skipPermissions = skipPermissions
window.finishOnboarding = finishOnboarding
window.closeOnboarding = closeOnboarding
