---
group: Configuration
icon: settings
order: 30
---
# Configuration

Scroll long pages with the mouse wheel or trackpad over their content, including nested settings cards. A scrollbar with its own gutter remains available at the right edge.

> Configuration has eight pages adapted from the current Handler QML. Each page owns an independent draft; changing pages does not save or discard it.

| Action | Result |
| --- | --- |
| Reset | Restore the saved values of the current page, retaining other drafts. |
| Apply | Validate and save the current page. Keep the window open. |
| Save | Validate and save all pages. Keep the window open; disable the button once all drafts are saved. |
| Close | Close a clean window. With pending edits, offer Save and close, Discard changes, or Continue editing. |
| Help | Open the article for the current page. |

Appearance changes preview immediately. Discard restores the last applied theme, palettes, icon set, language and animations. Other browser preferences take effect after Apply/Save. A storage error retains the editable draft and reports the failed save. If a later page fails during Save, pages already applied remain saved; this operation is not a cross-page transaction.

The desktop window keeps rounded corners when maximized and restored. The Close button, title controls
and unsaved-change guard remain available when changing configuration pages. Phones keep the full-screen layout.

## Pages and owners

| Page | Data owner and behavior |
| --- | --- |
| [Server](help://server_configuration) | Current browser origin/account, browser polling, and native server XML. |
| [Repositories](help://repository_configuration) | Native Config/Environment repository aliases; dedicated editor and server path checks. |
| [Projects](help://configuration.projects) | Native project catalogue, activation, record editing, creation and template export. |
| [Check-in Options](help://configuration.checkin) | New search tabs and new browser check-in jobs. |
| [Global](help://configuration.global) | Notification preferences and browser diagnostics. |
| [Appearance](help://appearance) | Shared Theme/controls, live preview and browser additions. |
| [Cache](help://configuration.cache) | Saved branch expansion and refresh of session data. |
| [Tasks](help://configuration.tasks) | New Task Manager/Inspector state and native task scheduling. |

Browser settings belong to this browser profile. `tactic_stream.preferences` contains repository/check-in/task/global/cache defaults; appearance, network and debug settings retain their existing separate keys. Account/project workspace state takes priority over defaults. Records and tickets are not copied into these preference entries. Server XML belongs to the installation and is shared by clients; changes marked Restart required need a backend restart. Project activation is immediate and does not wait for Apply.

The eight-page structure comes from `ConfigurationView.qml`, `Configuration*Page.qml` and `configuration.py`. Stream composes `Configuration.vue`, `ServerConfiguration.vue`, `FrameSettings.vue` and the existing feature owners. Desktop tray/DCC/rendering/endpoint presets and disk caches are not exposed as working browser controls. Repository Sync and S3 are excluded.

## Verification

Private SQLite/native Command tests and real Chromium verify current-page Apply/Reset, Save all without closing, validation, theme preview/discard, storage failure, reopen/reload, project activation, repository ACL/path checks, project ZIP export and check-in preview options. Fresh Qt/QML and Chromium captures cover all eight pages at 1400×940 and 900×620. Captures compare structure and geometry; they do not prove identical font rasterization or PostgreSQL/MySQL execution.

## Shared composition

Configuration now uses the same Tactic Frame navigation and explained settings rows in Handler and Stream. Long pages reserve space for a visible scrollbar; on phones the page selector replaces the sidebar. The current page keeps its own draft. Native preset saves preserve drafts on other pages. Local/DCC/tray/GPU options belong to Handler; browser XML, web paths and browser preferences remain Stream capabilities. No embedded browser is used by Handler.

On narrow repository editors, Reset and Sync use icon buttons with full tooltips; Save remains labelled. Project Save and template installation keep their complete captions in English and Russian.
