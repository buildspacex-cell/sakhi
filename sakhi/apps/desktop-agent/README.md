# Sakhi Desktop Agent

The Desktop Agent is the "hands" for Sakhi - it runs on your computer and executes actions (clicking, typing, scrolling) that Sakhi's "brain" (the API) decides.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Sakhi App     │ ←→  │   Sakhi API     │ ←→  │  Desktop Agent  │
│  (Control)      │     │   (Brain)       │     │   (Hands)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        ↓
                                                ┌─────────────────┐
                                                │  Your Computer  │
                                                │ (click, type,   │
                                                │  scroll, etc.)  │
                                                └─────────────────┘
```

## Features

- **Screen Capture**: Takes screenshots for the API to analyze
- **Mouse Control**: Click, double-click, right-click, drag, move
- **Keyboard Control**: Type text, press keys, keyboard shortcuts
- **Scroll**: Scroll up/down in any application
- **App Launch**: Open applications
- **Navigation**: Open URLs in browser
- **Auto-Update**: Seamlessly updates when new versions are available

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Install Dependencies

```bash
cd sakhi/apps/desktop-agent
npm install
```

### Development

```bash
npm run dev
```

### Build for Production

```bash
# Build for current platform
npm run package

# Build for specific platform
npm run package:mac
npm run package:win
npm run package:linux
```

## Configuration

The agent stores its configuration in:
- macOS: `~/Library/Application Support/sakhi-desktop-agent/config.json`
- Windows: `%APPDATA%/sakhi-desktop-agent/config.json`
- Linux: `~/.config/sakhi-desktop-agent/config.json`

### Environment Variables

- `SAKHI_API_URL`: API endpoint (default: `https://api.sakhi.ai`)

## Security

### Permissions Required

**macOS:**
- Accessibility permission (for mouse/keyboard control)
- Screen Recording permission (for screenshots)

**Windows:**
- No special permissions needed (but may trigger UAC)

**Linux:**
- X11 or Wayland access for input simulation

### How It Works

1. Agent registers with the API using a person ID
2. API returns an auth token for future requests
3. Agent sends periodic heartbeats to check for work
4. When a task is assigned, API sends actions to execute
5. Agent executes actions and sends back results + screenshots
6. API analyzes screenshots and sends next actions

### Data Privacy

- Screenshots are sent to the API for analysis
- No screenshots are stored locally
- Auth tokens are stored encrypted
- Device ID is hashed before sending to API

## Protocol

The agent communicates with the API using the Agent Protocol:

### Registration
```json
POST /api/v1/agent/register
{
  "agent_name": "My MacBook",
  "agent_type": "desktop",
  "device_id": "hashed-device-id",
  "capabilities": ["screen_capture", "mouse_click", ...],
  "platform": "macos"
}
```

### Heartbeat
```json
POST /api/v1/agent/{agent_id}/heartbeat
{
  "status": "online"
}
```

### Actions
```json
GET /api/v1/agent/{agent_id}/actions/pending

Response:
{
  "actions": [
    {
      "action_id": "...",
      "action_type": "click",
      "parameters": {"x": 500, "y": 300}
    }
  ]
}
```

## Troubleshooting

### "Accessibility permission required" on macOS

1. Open System Preferences → Security & Privacy → Privacy
2. Click Accessibility in the sidebar
3. Add Sakhi Agent to the list

### Agent not connecting

1. Check your internet connection
2. Verify the Person ID is correct
3. Check the API URL in settings

### Actions not executing

1. Ensure accessibility permissions are granted
2. Check if the target app is in focus
3. Verify the action coordinates are correct

## License

MIT
