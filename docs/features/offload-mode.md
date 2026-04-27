# Mobile Drop Mode

> Product + UX spec for the `Drop` mode alongside the existing `Talk to Sakhi` mobile experience.
>
> Status: shipped
>
> Last Updated: 2026-04-25
>
> **Rename note:** This feature was originally called `Drop`. Renamed to `Drop` on 2026-04-25 to align with the continuity-layer positioning (less wellness-adjacent, more action-oriented).

---

## Summary

Sakhi mobile keeps the current live conversation mode as `Talk to Sakhi` and adds a second mode, `Drop`.

`Drop` is for moments when the user wants to put things into Sakhi without expecting a reply. It must work both:

- online, when the user intentionally does not want a response
- offline, when the user still needs capture even without connectivity

The system still ingests offloaded content into the broader backend pipeline after successful sync, but the product contract is capture-only: no automatic Sakhi response is shown.

---

## Product Spec

### Problem

Early users are giving two closely related forms of feedback:

- "I want the app to take in what I'm saying while I'm offline too."
- "Sometimes I want to offload my stuff and I am not expecting answers."

The current mobile chat contract does not support either behavior well. The app posts directly to `POST /v2/turn` and expects a live response; when network access fails, the moment breaks instead of safely containing the user's expression.

### Goal

Add a second mobile mode that lets users safely capture thoughts without requiring:

- a live network connection
- an immediate Sakhi response

### Non-Goal

This spec does not add offline AI responses. `Drop` is not "chat without internet." It is safe capture plus later ingestion.

### Modes

#### `Talk to Sakhi`

- Existing mode
- User expects a live response
- Current online-first chat behavior remains
- Uses the current synchronous turn path

#### `Drop`

- New mode
- User does not expect a response
- Works online and offline
- Saves content locally first when needed
- Syncs later if the device is offline
- Runs backend ingestion after sync
- Does not generate an automatic Sakhi reply

### Core Principle

`Drop` is for capture, not conversation.

The system should take the user's content seriously, persist it safely, and process it after sync, but the user-facing contract remains:

- tap save
- see confirmation
- move on

### User Stories

- As a user, I want to dump what is in my head without waiting for a response.
- As a user, I want to keep using Sakhi when I have no internet.
- As a user, I want offloaded content to be safely retained after I close the app.
- As a user, I want Sakhi's existing conversation mode to remain unchanged when I am actively talking to it.

### Product Contract

#### `Talk to Sakhi`

- unchanged default conversational mode
- response expected
- if offline, current conversation behavior should not silently fabricate a response

#### `Drop`

- save-only mode
- no response expected
- online: save immediately, show confirmation
- offline: save locally, show confirmation, sync later
- after backend acceptance, the normal downstream ingestion pipeline still runs

### User-Visible States

Each offload item may show one of these states:

- `Saving...`
- `Saved`
- `Saved offline`
- `Syncing...`
- `Synced`
- `Needs retry`

### Backend Contract

`Drop` should not piggyback on the synchronous reply contract of `Talk to Sakhi`.

Recommended behavior:

- `Talk to Sakhi`
  - existing `POST /v2/turn`
  - synchronous reply + worker fan-out
- `Drop`
  - dedicated non-reply ingestion path
  - accepts text capture
  - persists the content
  - triggers the broader downstream pipeline after acceptance
  - supports idempotent retry using a stable client-generated id

### Data Model

Each locally captured offload item should retain at least:

- `client_id`
- `person_id`
- `mode = offload`
- `text`
- `created_at_device`
- `sync_status`
- `synced_at`
- `retry_count`
- optional `session_slug` or local thread identifier

### Local Storage Contract

Local offloads must:

- survive app kill and reopen
- preserve capture order
- retry safely after reconnect
- avoid leaking free text into analytics or debug telemetry

### Acceptance Criteria

- A user can choose `Drop` and save text online without receiving a reply.
- A user can choose `Drop` and save text offline without losing it.
- Saved offline entries survive app relaunch.
- Pending entries sync automatically when the device reconnects.
- Synced entries run through the backend ingestion pipeline.
- `Talk to Sakhi` remains intact for the current online conversation UX.
- During the current beta, `Talk to Sakhi` and `Drop` both feed one shared active continuity window.
- The beta continuity window is `180 days`; older entries may still exist, but they no longer shape free continuity surfaces unless the user upgrades later.

---

## UX Spec

### UX Principles

- Do not make existing users relearn the app just to add offline safety.
- Do not force the user to choose between modes on every launch.
- Make `Drop` feel like containment, not like a degraded form of chat.
- Keep copy simple and emotionally legible.

### Entry Model

The user should not have to choose between `Talk to Sakhi` and `Drop` every time.

Recommended behavior:

1. First launch after this feature is introduced:
   show a mode chooser so the user understands the distinction.
2. Thereafter:
   remember the last-used mode and open directly into it.
3. Always:
   provide one-tap switching between modes from within the active screen.

### Mode Identity

The two modes should not rely on text alone. Each mode gets a stable icon treatment that is introduced on first choice and then repeated inside the active screen.

- `Talk to Sakhi`
  - chat icon
- `Drop`
  - archive / save icon

Rule:

- the first-time chooser teaches both the mode copy and the icon
- once the user chooses a mode, that same icon should appear in the footer mode toggle so the mode remains legible without repeating a separate mode label elsewhere
- the footer mode toggle is the single source of truth for current mode inside the active screen
- do not repeat the active mode in the top header if the footer toggle is already clear
- use subtle ambient screen treatment to differentiate modes:
  - `Talk to Sakhi` can feel a little brighter and more live
  - `Drop` can feel more contained and quieter
- pricing pressure should come from continuity duration, not from blocking capture
- `Drop` remains available in free; what is limited is how long Talk + Drop stay active inside the continuity layer

### Home Screen Change

The signed-in home changes from a single route into chat to a lightweight entry surface that can either:

- teach the two modes on first use, or
- remember the last-used mode and present one dominant CTA

The screen should not become a dashboard. It stays quiet and sparse.

---

## Screen-Level UX Spec

### Screen 1: First-Time Mode Chooser

Shown only:

- on first launch after this feature ships
- after sign-in if the user has never chosen a mode before
- when the user explicitly taps `Change mode`

#### Purpose

Teach the distinction between:

- `Talk to Sakhi`
- `Drop`

#### Content

Headline:

`This is a quiet space to unload your mind.`

Subhead:

`What do you need right now?`

Primary cards:

- `Talk to Sakhi`
  - chat icon
  - `Have a conversation. Get a response.`
- `Drop`
  - archive / save icon
  - `Just put it down. No response expected. Works offline too.`

Microcopy:

`You can switch anytime. Sakhi will remember what you used last.`

#### Text Mockup

```text
------------------------------------------------
This is a quiet space to unload your mind.

What do you need right now?

┌──────────────────────────────────────────────┐
│ [chat icon] Talk to Sakhi                   │
│ Have a conversation. Get a response.        │
│                                              │
│ [ Start Talking ]                           │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ [archive icon] Drop                      │
│ Just put it down. No response expected.     │
│ Works offline too.                          │
│                                              │
│ [ Start Droping ]                        │
└──────────────────────────────────────────────┘

You can switch anytime.
------------------------------------------------
```

### Screen 2: Remembered Home State

After the first explicit choice, the app remembers the user's last-used mode and stops forcing a full choice every launch.

#### If last used was `Talk to Sakhi`

```text
------------------------------------------------
This is a quiet space to unload your mind.

[ Continue Talking ]      <- primary CTA
Drop instead
------------------------------------------------
```

#### If last used was `Drop`

```text
------------------------------------------------
This is a quiet space to unload your mind.

[ Continue Droping ]   <- primary CTA
Talk to Sakhi instead
------------------------------------------------
```

#### UX Rule

- one primary CTA
- one secondary text action to switch modes
- no need to re-decide from scratch every launch

### Screen 3: Talk to Sakhi

This remains the current chat screen with only minimal additions:

- one clear top mode switch with strong active highlighting
- one-tap switch into `Drop`
- no duplicate mode label near the composer/footer
- optional offline banner if there is no network

#### Online State

Behavior:

- same as current chat
- send button semantics unchanged
- Sakhi replies live

Possible top affordance:

`Mode: Talk to Sakhi    Switch to Drop`

#### Offline State

If the user is in `Talk to Sakhi` and offline, the UI should make the constraint obvious.

Recommended copy:

`You're offline. Switch to Drop to save this without a response.`

This avoids quietly changing the meaning of `Talk to Sakhi`.

### Screen 4: Drop

This should feel calmer and more contained than chat.

#### Purpose

Let the user put things into Sakhi without expecting a response.

#### Layout

- simple header with mode label
- optional online/offline status chip
- chronological list of recent offloads and statuses
- stronger top-level mode highlighting rather than a duplicate composer/footer label
- input composer with `Save` semantics, not `Send`

#### Header Copy

- Title: `Drop`
- Subtitle:
  - online: `Put it down. Sakhi will take it in.`
  - offline: `Put it down. I'll save it and sync later.`

#### Composer Copy

Placeholder:

`What do you need to put down?`

Primary CTA:

- online: `Save`
- offline: `Save offline`

#### Online Mockup

```text
------------------------------------------------
Drop                               [Online]

Put it down. Sakhi will take it in.

[ recent saved offloads list ]

------------------------------------------------
What do you need to put down?

[ multiline input area                       ]

                              [ Save ]
------------------------------------------------
```

#### Offline Mockup

```text
------------------------------------------------
Drop                              [Offline]

Put it down. I'll save it and sync later.

[ recent offloads list ]
- "I can't hold all of this today..."   Saved offline
- "Need to stop pretending I can..."    Saved offline

------------------------------------------------
What do you need to put down?

[ multiline input area                       ]

                        [ Save offline ]
------------------------------------------------
```

### Screen 5: Drop Item States

Each item in the list should show a small, quiet state label.

Examples:

- `Saved`
- `Saved offline`
- `Syncing...`
- `Synced`
- `Needs retry`

The state styling should be subtle and non-alarming. `Drop` is a calming surface, not a diagnostics console.

### Screen 6: Reconnect / Sync Flow

When the app comes back online:

- pending offloads transition from `Saved offline` to `Syncing...`
- on success they become `Synced`
- on failure they become `Needs retry`

#### Reconnect Banner

Recommended temporary banner:

`Back online. Syncing your offloads...`

This should auto-dismiss after successful sync.

### Screen 7: Retry State

If sync fails:

- keep the local content
- mark the item `Needs retry`
- offer a lightweight action:
  - `Retry`
  - optional `Delete`

Do not present a disruptive modal unless the queue is blocked repeatedly.

#### Retry Mockup

```text
"I am more tired than I am admitting."   Needs retry   [Retry]
```

---

## UX Flows

### Flow A: First-Time User of the Feature

1. User signs in or opens the app after the feature release.
2. App shows mode chooser.
3. User taps `Talk to Sakhi` or `Drop`.
4. App stores `last_used_mode`.
5. Future launches default into that mode.

### Flow B: Repeat User, Last Used `Talk to Sakhi`

1. User opens app.
2. App routes directly into `Talk to Sakhi`.
3. User can switch to `Drop` from the header/action.

### Flow C: Repeat User, Last Used `Drop`

1. User opens app.
2. App routes directly into `Drop`.
3. User can switch to `Talk to Sakhi` from the header/action.

### Flow D: Drop While Online

1. User enters `Drop`.
2. Types text.
3. Taps `Save`.
4. UI shows `Saving...` then `Saved`.
5. Backend ingestion runs without generating a reply bubble.

### Flow E: Drop While Offline

1. User enters `Drop`.
2. Types text.
3. Taps `Save offline`.
4. UI shows `Saved offline`.
5. App stores the item locally.
6. On reconnect, app syncs automatically.
7. UI updates to `Synced` or `Needs retry`.

---

## Open Questions

- Should `Drop` be a visually distinct dedicated screen, or a mode inside the existing chat shell?
- Should offloaded items live in their own timeline, or should they later appear mixed into conversation history with a distinct type marker?
- What should the dedicated backend route be called for no-reply ingestion?
- Should `Talk to Sakhi` while offline offer any capture affordance, or always direct the user into `Drop`?

---

## Recommendation

For MVP:

- keep `Talk to Sakhi` exactly as it is when online
- add `Drop` as a separate explicit mode
- remember the user's last-used mode
- make `Drop` the single place where both no-response capture and offline capture live
- do not generate automatic Sakhi replies for offloaded content

This keeps the current experience stable while introducing a clear, trustworthy second contract for capture.
