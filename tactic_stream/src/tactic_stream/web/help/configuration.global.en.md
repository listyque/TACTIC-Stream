---
group: Configuration
icon: settings
order: 35
---
# Global preferences

> Global controls browser notifications and diagnostics. Apply/Reset affect this page alone, including its DebugSettings draft.

Activity feed notifications and Message notifications switch incoming-event toasts on or off. Event history, feed records and message delivery remain available. Debug Log retention/collection/automatic diagnostic saving use the existing DebugSettings owner; its controls are staged until Apply. Diagnostic exports and deletion actions remain explicit actions in Debug Log.

Saved values live in `tactic_stream.preferences.global` and `tactic_stream.debug_log`. Their page save restores previous storage values if a browser write fails, keeps the draft and shows an error. Appearance preview is independent. Tray integration, local worker pools, Handler Server and DCC connections are desktop features; browser requests use native server workers configured on Server.
