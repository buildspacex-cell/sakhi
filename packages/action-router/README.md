# @sakhi/action-router

Consumes `plan.ready` events and executes the “Hands” layer: creating tasks, proposing calendar blocks, and scheduling nudges. Emits `action.routed` after downstream integrations fire.

Implement the `createTask`, `proposeBlock`, and `scheduleNudge` callbacks to integrate with Notion, Linear, Google Calendar, etc.
