/**
 * Renderer Script
 * ---------------
 * UI logic for the Sakhi Desktop Agent dashboard.
 */

// Elements
const statusIndicator = document.getElementById('status-indicator')!
const statusDot = statusIndicator.querySelector('.status-dot')!
const statusText = statusIndicator.querySelector('.status-text')!
const statusDetail = document.getElementById('status-detail')!

const registrationSection = document.getElementById('registration-section')!
const registrationForm = document.getElementById('registration-form')!
const personIdInput = document.getElementById('person-id') as HTMLInputElement
const agentNameInput = document.getElementById('agent-name') as HTMLInputElement

const taskSection = document.getElementById('task-section')!
const activeTask = document.getElementById('active-task')!
const noTask = document.getElementById('no-task')!
const taskName = document.getElementById('task-name')!
const taskStatus = document.getElementById('task-status')!
const actionsCount = document.getElementById('actions-count')!
const stopTaskBtn = document.getElementById('stop-task-btn')!

const actionsSection = document.getElementById('actions-section')!
const screenshotBtn = document.getElementById('screenshot-btn')!
const openAppBtn = document.getElementById('open-app-btn')!

const statsSection = document.getElementById('stats-section')!
const totalActions = document.getElementById('total-actions')!
const lastHeartbeat = document.getElementById('last-heartbeat')!

const versionEl = document.getElementById('version')!

// State
interface AgentState {
  status: 'idle' | 'registered' | 'active' | 'executing' | 'paused' | 'error'
  agentId: string | null
  sessionId: string | null
  currentTask: string | null
  lastHeartbeat: Date | null
  actionsExecuted: number
  lastError: string | null
}

let currentState: AgentState | null = null

/**
 * Update UI based on agent state.
 */
function updateUI(state: AgentState): void {
  currentState = state

  // Update status indicator
  statusDot.className = 'status-dot'

  switch (state.status) {
    case 'idle':
      statusText.textContent = 'Not Connected'
      statusDetail.textContent = 'Connect to start using the agent'
      break
    case 'registered':
      statusDot.classList.add('connected')
      statusText.textContent = 'Connected'
      statusDetail.textContent = 'Ready to receive tasks'
      break
    case 'active':
      statusDot.classList.add('active')
      statusText.textContent = 'Active'
      statusDetail.textContent = state.currentTask || 'Working on task...'
      break
    case 'executing':
      statusDot.classList.add('active')
      statusText.textContent = 'Executing...'
      statusDetail.textContent = 'Running actions'
      break
    case 'paused':
      statusDot.classList.add('connected')
      statusText.textContent = 'Paused'
      statusDetail.textContent = 'Task paused'
      break
    case 'error':
      statusDot.classList.add('error')
      statusText.textContent = 'Error'
      statusDetail.textContent = state.lastError || 'Unknown error'
      break
  }

  // Show/hide sections based on state
  const isConnected = state.status !== 'idle'

  registrationSection.style.display = isConnected ? 'none' : 'block'
  taskSection.style.display = isConnected ? 'block' : 'none'
  actionsSection.style.display = isConnected ? 'block' : 'none'
  statsSection.style.display = isConnected ? 'flex' : 'none'

  // Update task section
  if (state.sessionId) {
    activeTask.style.display = 'block'
    noTask.style.display = 'none'
    taskName.textContent = state.currentTask || 'Running task...'
    taskStatus.textContent = state.status === 'executing' ? 'Executing' : 'Active'
    taskStatus.className = 'task-status' + (state.status === 'executing' ? ' executing' : '')
    actionsCount.textContent = `${state.actionsExecuted} action${state.actionsExecuted !== 1 ? 's' : ''} completed`
  } else {
    activeTask.style.display = 'none'
    noTask.style.display = 'block'
  }

  // Update stats
  totalActions.textContent = state.actionsExecuted.toString()
  if (state.lastHeartbeat) {
    const ago = getTimeAgo(new Date(state.lastHeartbeat))
    lastHeartbeat.textContent = ago
  } else {
    lastHeartbeat.textContent = '-'
  }
}

/**
 * Get relative time string.
 */
function getTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)

  if (seconds < 5) return 'Just now'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

/**
 * Handle registration form submit.
 */
async function handleRegister(event: Event): Promise<void> {
  event.preventDefault()

  const personId = personIdInput.value.trim()
  if (!personId) {
    alert('Please enter your Person ID')
    return
  }

  const agentName = agentNameInput.value.trim() || undefined

  try {
    statusText.textContent = 'Connecting...'
    const state = await window.sakhi.register(personId, agentName)
    updateUI(state)
  } catch (error) {
    console.error('Registration failed:', error)
    statusText.textContent = 'Connection failed'
    statusDetail.textContent = error instanceof Error ? error.message : 'Unknown error'
  }
}

/**
 * Handle stop task button.
 */
async function handleStopTask(): Promise<void> {
  if (!confirm('Stop the current task?')) return

  try {
    const state = await window.sakhi.stopTask()
    updateUI(state)
  } catch (error) {
    console.error('Failed to stop task:', error)
  }
}

/**
 * Handle screenshot button.
 */
async function handleScreenshot(): Promise<void> {
  try {
    screenshotBtn.textContent = '📸 Capturing...'
    await window.sakhi.screenshot()
    screenshotBtn.textContent = '📸 Screenshot'
  } catch (error) {
    console.error('Screenshot failed:', error)
    screenshotBtn.textContent = '📸 Screenshot'
  }
}

/**
 * Handle open app button.
 */
function handleOpenApp(): void {
  window.open('https://app.sakhi.ai', '_blank')
}

/**
 * Initialize the UI.
 */
async function init(): Promise<void> {
  // Set version
  versionEl.textContent = `v${window.sakhi.getVersion()}`

  // Get initial state
  try {
    const state = await window.sakhi.getState()
    updateUI(state)
  } catch (error) {
    console.error('Failed to get state:', error)
    statusText.textContent = 'Error'
    statusDetail.textContent = 'Failed to connect to agent'
  }

  // Listen for state changes
  window.sakhi.onStateChange((state) => {
    updateUI(state)
  })

  // Setup event listeners
  registrationForm.addEventListener('submit', handleRegister)
  stopTaskBtn.addEventListener('click', handleStopTask)
  screenshotBtn.addEventListener('click', handleScreenshot)
  openAppBtn.addEventListener('click', handleOpenApp)

  // Update heartbeat time every second
  setInterval(() => {
    if (currentState?.lastHeartbeat) {
      lastHeartbeat.textContent = getTimeAgo(new Date(currentState.lastHeartbeat))
    }
  }, 1000)
}

// Start
init()
