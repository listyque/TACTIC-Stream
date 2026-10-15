import materialMap from './assets/fonts/materialdesignicons-webfont-charmap.json'
import solidMap from './assets/fonts/fontawesome5-solid-webfont-charmap.json'
import regularMap from './assets/fonts/fontawesome5-regular-webfont-charmap.json'
import fluentMap from './assets/fonts/fluent-system-icons-resizable.json'

export const iconMaps = { 'material-design': materialMap, 'fontawesome-solid': solidMap, 'fontawesome-outline': regularMap, 'fluent-regular': {}, 'fluent-filled': {} }
for (const [name, code] of Object.entries(fluentMap)) {
  const match = /^ic_fluent_(.+)_20_(regular|filled)$/.exec(name)
  if (match) iconMaps['fluent-' + match[2]][match[1].replaceAll('_', '-')] = code
}
const iconCode = code => String.fromCodePoint(typeof code === 'number' ? code : parseInt(code, 16))

// Semantic glyphs from Handler MaterialIcon.qml and official bundled charmaps.
export const icons = {
  "material-design": {
    "menu": [
      "material-design",
      "󰍜"
    ],
    "close": [
      "material-design",
      "󰅖"
    ],
    "more": [
      "material-design",
      "󰇙"
    ],
    "edit": [
      "material-design",
      "󰏫"
    ],
    "link": [
      "material-design",
      "󰌷"
    ],
    "activity": [
      "material-design",
      "󰐰"
    ],
    "connection": [
      "material-design",
      "󰌘"
    ],
    "queue": [
      "material-design",
      "󰅧"
    ],
    "history": [
      "material-design",
      "󰋚"
    ],
    "appearance": [
      "material-design",
      "󰔎"
    ],
    "settings": [
      "material-design",
      "󰒓"
    ],
    "refresh": [
      "material-design",
      "󰑐"
    ],
    "add": [
      "material-design",
      "󰐕"
    ],
    "table": [
      "fontawesome-solid",
      ""
    ],
    "search": [
      "material-design",
      "󰍉"
    ],
    "code": [
      "material-design",
      "󰅴"
    ],
    "logout": [
      "material-design",
      "󰍃"
    ]
  },
  "fontawesome-solid": {
    "menu": [
      "fontawesome-solid",
      ""
    ],
    "close": [
      "fontawesome-solid",
      ""
    ],
    "more": [
      "fontawesome-solid",
      ""
    ],
    "edit": [
      "fontawesome-solid",
      ""
    ],
    "link": [
      "fontawesome-solid",
      ""
    ],
    "activity": [
      "fontawesome-solid",
      ""
    ],
    "connection": [
      "fontawesome-solid",
      ""
    ],
    "queue": [
      "fontawesome-solid",
      ""
    ],
    "history": [
      "fontawesome-solid",
      ""
    ],
    "appearance": [
      "fontawesome-solid",
      ""
    ],
    "settings": [
      "fontawesome-solid",
      ""
    ],
    "refresh": [
      "fontawesome-solid",
      ""
    ],
    "add": [
      "fontawesome-solid",
      ""
    ],
    "table": [
      "fontawesome-solid",
      ""
    ],
    "search": [
      "fontawesome-solid",
      ""
    ],
    "code": [
      "fontawesome-solid",
      ""
    ],
    "logout": [
      "fontawesome-solid",
      ""
    ]
  },
  "fontawesome-outline": {
    "menu": [
      "fontawesome-solid",
      ""
    ],
    "close": [
      "fontawesome-solid",
      ""
    ],
    "more": [
      "fontawesome-solid",
      ""
    ],
    "edit": [
      "fontawesome-outline",
      ""
    ],
    "link": [
      "fontawesome-solid",
      ""
    ],
    "activity": [
      "fontawesome-solid",
      ""
    ],
    "connection": [
      "fontawesome-solid",
      ""
    ],
    "queue": [
      "fontawesome-solid",
      ""
    ],
    "history": [
      "fontawesome-solid",
      ""
    ],
    "appearance": [
      "fontawesome-solid",
      ""
    ],
    "settings": [
      "fontawesome-solid",
      ""
    ],
    "refresh": [
      "fontawesome-solid",
      ""
    ],
    "add": [
      "fontawesome-solid",
      ""
    ],
    "table": [
      "fontawesome-solid",
      ""
    ],
    "search": [
      "fontawesome-solid",
      ""
    ],
    "code": [
      "fontawesome-solid",
      ""
    ],
    "logout": [
      "fontawesome-solid",
      ""
    ]
  },
  "fluent-regular": {
    "menu": [
      "fontawesome-solid",
      ""
    ],
    "close": [
      "fluent-regular",
      ""
    ],
    "more": [
      "fluent-regular",
      ""
    ],
    "edit": [
      "fluent-regular",
      ""
    ],
    "link": [
      "fluent-regular",
      ""
    ],
    "activity": [
      "fluent-regular",
      ""
    ],
    "connection": [
      "fluent-regular",
      ""
    ],
    "queue": [
      "fluent-regular",
      ""
    ],
    "history": [
      "fluent-regular",
      ""
    ],
    "appearance": [
      "fluent-regular",
      ""
    ],
    "settings": [
      "fluent-regular",
      ""
    ],
    "refresh": [
      "fluent-regular",
      ""
    ],
    "add": [
      "fluent-regular",
      ""
    ],
    "table": [
      "fluent-regular",
      ""
    ],
    "search": [
      "fluent-regular",
      ""
    ],
    "code": [
      "fluent-regular",
      ""
    ],
    "logout": [
      "fluent-regular",
      ""
    ]
  },
  "fluent-filled": {
    "menu": [
      "fontawesome-solid",
      ""
    ],
    "close": [
      "fluent-filled",
      ""
    ],
    "more": [
      "fluent-filled",
      ""
    ],
    "edit": [
      "fluent-filled",
      ""
    ],
    "link": [
      "fluent-filled",
      ""
    ],
    "activity": [
      "fluent-filled",
      ""
    ],
    "connection": [
      "fluent-filled",
      ""
    ],
    "queue": [
      "fluent-filled",
      ""
    ],
    "history": [
      "fluent-filled",
      ""
    ],
    "appearance": [
      "fluent-filled",
      ""
    ],
    "settings": [
      "fluent-filled",
      ""
    ],
    "refresh": [
      "fluent-filled",
      ""
    ],
    "add": [
      "fluent-filled",
      ""
    ],
    "table": [
      "fluent-filled",
      ""
    ],
    "search": [
      "fluent-filled",
      ""
    ],
    "code": [
      "fluent-filled",
      ""
    ],
    "logout": [
      "fluent-filled",
      ""
    ]
  }
}

// Configuration glyphs from the same official Handler charmaps.
const configurationIcons = {
  "material-design": {
    "save": [
      "material-design",
      "󰆓"
    ],
    "undo": [
      "material-design",
      "󰕌"
    ],
    "check": [
      "material-design",
      "󰄬"
    ],
    "help": [
      "material-design",
      "󰋖"
    ],
    "database": [
      "material-design",
      "󰆼"
    ],
    "folder": [
      "material-design",
      "󰉋"
    ],
    "security": [
      "material-design",
      "󰦝"
    ]
  },
  "fontawesome-solid": {
    "save": [
      "fontawesome-solid",
      ""
    ],
    "undo": [
      "fontawesome-solid",
      ""
    ],
    "check": [
      "fontawesome-solid",
      ""
    ],
    "help": [
      "fontawesome-solid",
      ""
    ],
    "database": [
      "fontawesome-solid",
      ""
    ],
    "folder": [
      "fontawesome-solid",
      ""
    ],
    "security": [
      "fontawesome-solid",
      ""
    ]
  },
  "fontawesome-outline": {
    "save": [
      "fontawesome-outline",
      ""
    ],
    "undo": [
      "fontawesome-solid",
      ""
    ],
    "check": [
      "fontawesome-solid",
      ""
    ],
    "help": [
      "fontawesome-solid",
      ""
    ],
    "database": [
      "fontawesome-solid",
      ""
    ],
    "folder": [
      "fontawesome-outline",
      ""
    ],
    "security": [
      "fontawesome-solid",
      ""
    ]
  },
  "fluent-regular": {
    "save": [
      "fluent-regular",
      ""
    ],
    "undo": [
      "fluent-regular",
      ""
    ],
    "check": [
      "fluent-regular",
      ""
    ],
    "help": [
      "fluent-regular",
      ""
    ],
    "database": [
      "fluent-regular",
      ""
    ],
    "folder": [
      "fluent-regular",
      ""
    ],
    "security": [
      "fluent-regular",
      ""
    ]
  },
  "fluent-filled": {
    "save": [
      "fluent-filled",
      ""
    ],
    "undo": [
      "fluent-filled",
      ""
    ],
    "check": [
      "fluent-filled",
      ""
    ],
    "help": [
      "fluent-filled",
      ""
    ],
    "database": [
      "fluent-filled",
      ""
    ],
    "folder": [
      "fluent-filled",
      ""
    ],
    "security": [
      "fluent-filled",
      ""
    ]
  }
}
for (const [pack, glyphs] of Object.entries(configurationIcons)) Object.assign(icons[pack], glyphs)

// Official Handler glyphs for the administration sections.
const administrationIcons = {
  "material-design": {
    "user": [
      "material-design",
      "󰀄"
    ],
    "groups": [
      "material-design",
      "󰡉"
    ],
    "schema": [
      "material-design",
      "󰙅"
    ],
    "workflow": [
      "material-design",
      "󰘬"
    ],
    "sobject": [
      "material-design",
      "󰆦"
    ],
    "info": [
      "material-design",
      "󰋼"
    ],
    "minus": [
      "material-design",
      "󰍴"
    ],
    "reset": [
      "material-design",
      "󰕌"
    ],
    "filter": [
      "material-design",
      "󰈲"
    ],
    "previous": [
      "material-design",
      "󰅁"
    ],
    "next": [
      "material-design",
      "󰅂"
    ],
    "sort": [
      "material-design",
      "󰒺"
    ]
  },
  "fontawesome-solid": {
    "user": [
      "fontawesome-solid",
      ""
    ],
    "groups": [
      "fontawesome-solid",
      ""
    ],
    "schema": [
      "fontawesome-solid",
      ""
    ],
    "workflow": [
      "fontawesome-solid",
      ""
    ],
    "sobject": [
      "fontawesome-solid",
      ""
    ],
    "info": [
      "fontawesome-solid",
      ""
    ],
    "minus": [
      "fontawesome-solid",
      ""
    ],
    "reset": [
      "fontawesome-solid",
      ""
    ],
    "filter": [
      "fontawesome-solid",
      ""
    ],
    "previous": [
      "fontawesome-solid",
      ""
    ],
    "next": [
      "fontawesome-solid",
      ""
    ],
    "sort": [
      "fontawesome-solid",
      ""
    ]
  },
  "fontawesome-outline": {
    "user": [
      "fontawesome-solid",
      ""
    ],
    "groups": [
      "fontawesome-solid",
      ""
    ],
    "schema": [
      "fontawesome-solid",
      ""
    ],
    "workflow": [
      "fontawesome-solid",
      ""
    ],
    "sobject": [
      "fontawesome-solid",
      ""
    ],
    "info": [
      "fontawesome-solid",
      ""
    ],
    "minus": [
      "fontawesome-solid",
      ""
    ],
    "reset": [
      "fontawesome-solid",
      ""
    ],
    "filter": [
      "fontawesome-solid",
      ""
    ],
    "previous": [
      "fontawesome-solid",
      ""
    ],
    "next": [
      "fontawesome-solid",
      ""
    ],
    "sort": [
      "fontawesome-solid",
      ""
    ]
  },
  "fluent-regular": {
    "user": [
      "fluent-regular",
      ""
    ],
    "groups": [
      "fluent-regular",
      ""
    ],
    "schema": [
      "fluent-regular",
      ""
    ],
    "workflow": [
      "fluent-regular",
      ""
    ],
    "sobject": [
      "fluent-regular",
      ""
    ],
    "info": [
      "fluent-regular",
      ""
    ],
    "minus": [
      "fluent-regular",
      ""
    ],
    "reset": [
      "fluent-regular",
      ""
    ],
    "filter": [
      "fluent-regular",
      ""
    ],
    "previous": [
      "fluent-regular",
      ""
    ],
    "next": [
      "fluent-regular",
      ""
    ],
    "sort": [
      "fluent-regular",
      ""
    ]
  },
  "fluent-filled": {
    "user": [
      "fluent-filled",
      ""
    ],
    "groups": [
      "fluent-filled",
      ""
    ],
    "schema": [
      "fluent-filled",
      ""
    ],
    "workflow": [
      "fluent-filled",
      ""
    ],
    "sobject": [
      "fluent-filled",
      ""
    ],
    "info": [
      "fluent-filled",
      ""
    ],
    "minus": [
      "fluent-filled",
      ""
    ],
    "reset": [
      "fluent-filled",
      ""
    ],
    "filter": [
      "fluent-filled",
      ""
    ],
    "previous": [
      "fluent-filled",
      ""
    ],
    "next": [
      "fluent-filled",
      ""
    ],
    "sort": [
      "fluent-filled",
      ""
    ]
  }
}
for (const [pack, glyphs] of Object.entries(administrationIcons)) Object.assign(icons[pack], glyphs)

// Official copy glyphs from the bundled Handler font charmaps.
const copyIcons = {
  "material-design": [
    "material-design",
    "󰆏"
  ],
  "fontawesome-solid": [
    "fontawesome-solid",
    ""
  ],
  "fontawesome-outline": [
    "fontawesome-regular",
    ""
  ],
  "fluent-regular": [
    "fluent-regular",
    ""
  ],
  "fluent-filled": [
    "fluent-filled",
    ""
  ]
}
for (const [pack, glyph] of Object.entries(copyIcons)) icons[pack].copy = glyph

// Delete glyphs from the same official Handler font charmaps.
const deleteIcons = {
  'material-design': ['material-design', '\u{f01b4}'],
  'fontawesome-solid': ['fontawesome-solid', '\uf2ed'],
  'fontawesome-outline': ['fontawesome-regular', '\uf2ed'],
  'fluent-regular': ['fluent-regular', '\ue66d'],
  'fluent-filled': ['fluent-filled', '\ue66c'],
}
for (const [pack, glyph] of Object.entries(deleteIcons)) icons[pack].delete = glyph

const downloadIcons = {
  'material-design': ['material-design', '\u{f01da}'],
  'fontawesome-solid': ['fontawesome-solid', '\uf019'],
  'fontawesome-outline': ['fontawesome-solid', '\uf019'],
  'fluent-regular': ['fluent-regular', String.fromCodePoint(57565)],
  'fluent-filled': ['fluent-filled', String.fromCodePoint(57564)],
}
for (const [pack, glyph] of Object.entries(downloadIcons)) icons[pack].download = glyph
for (const pack of Object.values(icons)) pack['more-vert'] = pack.more

// Handler push-pin aliases, using the official bundled charmaps.
const pinIcons = {
  'material-design': ['material-design', '\u{f0403}'],
  'fontawesome-solid': ['fontawesome-solid', '\uf08d'],
  'fontawesome-outline': ['fontawesome-solid', '\uf08d'],
  'fluent-regular': ['fluent-regular', String.fromCodePoint(61045)],
  'fluent-filled': ['fluent-filled', String.fromCodePoint(61044)],
}
for (const [pack, glyph] of Object.entries(pinIcons)) icons[pack].pin = glyph

// Preserve legacy sidebar glyphs alongside current Handler set:name values.
for (const pack of ['material-design', 'fontawesome-solid', 'fontawesome-outline']) {
  const family = pack === 'fontawesome-outline' ? 'fontawesome-solid' : pack
  const code = (family === 'material-design' ? materialMap : solidMap)[family === 'material-design' ? 'view-stream' : 'stream']
  icons[pack].stream = [family, String.fromCodePoint(parseInt(code, 16))]
}
// Current Handler MaterialIcon.qml aliases used by Activity Feed.
const activityAliases = {
  "material-design": {
    "commit-queue": "cloud-upload",
    "view-kanban": "view-column",
    "task-alt": "checkbox-marked-circle",
    "settings-suggest": "cog-refresh",
    "dashboard-customize": "view-dashboard-edit",
    "dynamic-feed": "chart-timeline-variant",
    "sync": "sync",
    "check-circle": "check-circle",
    "tab": "tab",
    "dns": "server",
    "desktop": "monitor",
    "delete-sweep": "delete-sweep",
    "priority-high": "alert",
    "warning": "alert",
    "info": "information",
    "notifications": "bell",
    "open-in-full": "arrow-expand-all",
    "window-restore": "window-restore",
    "activity-feed": "history",
    "task": "clipboard-check",
    "notes": "note-text",
    "snapshot": "camera",
    "select-all": "select-all",
    "inventory-2": "archive",
    "system-activity": "pulse",
    "schedule": "calendar-clock",
    "description": "text-box",
    "book-open": "book-open",
    "groups": "account-group",
    "account-tree": "file-tree",
    "control-point-duplicate": "content-duplicate",
    "fact-check": "clipboard-check-outline",
    "text-fields": "format-text",
    "attachments-editor": "paperclip",
    "create-article": "file-document-plus",
    "code-block": "code-block-tags",
    "small-text": "format-font-size-decrease",
    "format-quote": "format-quote-open"
  },
  "fontawesome-solid": {
    "commit-queue": "cloud-upload-alt",
    "view-kanban": "columns",
    "task-alt": "check-circle",
    "settings-suggest": "tools",
    "dashboard-customize": "th-large",
    "dynamic-feed": "stream",
    "sync": "sync-alt",
    "check-circle": "check-circle",
    "tab": "window-maximize",
    "dns": "server",
    "desktop": "desktop",
    "delete-sweep": "broom",
    "priority-high": "exclamation",
    "warning": "exclamation-triangle",
    "info": "info-circle",
    "notifications": "bell",
    "open-in-full": "expand",
    "window-restore": "window-restore",
    "activity-feed": "history",
    "task": "tasks",
    "notes": "sticky-note",
    "snapshot": "camera",
    "select-all": "check-double",
    "inventory-2": "archive",
    "system-activity": "heartbeat",
    "schedule": "clock",
    "groups": "users",
    "description": "file-alt",
    "book-open": "book-open",
    "account-tree": "project-diagram",
    "control-point-duplicate": "clone",
    "fact-check": "clipboard-check",
    "text-fields": "font",
    "attachments-editor": "paperclip",
    "create-article": "plus-square",
    "code-block": "code",
    "small-text": "text-height",
    "format-quote": "quote-left"
  },
  "fontawesome-outline": {
    "commit-queue": "cloud-upload-alt",
    "view-kanban": "columns",
    "task-alt": "check-circle",
    "settings-suggest": "tools",
    "dashboard-customize": "th-large",
    "dynamic-feed": "stream",
    "sync": "sync-alt",
    "check-circle": "check-circle",
    "tab": "window-maximize",
    "dns": "server",
    "desktop": "desktop",
    "delete-sweep": "broom",
    "priority-high": "exclamation",
    "warning": "exclamation-triangle",
    "info": "info-circle",
    "notifications": "bell",
    "open-in-full": "expand",
    "window-restore": "window-restore",
    "activity-feed": "history",
    "task": "tasks",
    "notes": "sticky-note",
    "snapshot": "camera",
    "select-all": "check-double",
    "inventory-2": "archive",
    "system-activity": "heartbeat",
    "schedule": "clock",
    "groups": "users",
    "description": "file-alt",
    "book-open": "book-open",
    "account-tree": "project-diagram",
    "control-point-duplicate": "clone",
    "fact-check": "clipboard-check",
    "text-fields": "font",
    "attachments-editor": "paperclip",
    "create-article": "plus-square",
    "code-block": "code",
    "small-text": "text-height",
    "format-quote": "quote-left"
  },
  "fluent-regular": {
    "commit-queue": "cloud-arrow-up",
    "view-kanban": "grid-kanban",
    "task-alt": "clipboard-task",
    "settings-suggest": "settings-cog-multiple",
    "dashboard-customize": "grid-dots",
    "dynamic-feed": "timeline",
    "sync": "arrow-sync",
    "check-circle": "checkmark-circle",
    "tab": "tab-desktop",
    "dns": "server",
    "desktop": "desktop",
    "delete-sweep": "broom",
    "priority-high": "important",
    "warning": "warning",
    "info": "info",
    "notifications": "alert",
    "open-in-full": "arrow-expand",
    "window-restore": "window",
    "activity-feed": "history",
    "task": "clipboard-task",
    "notes": "note",
    "snapshot": "camera",
    "select-all": "select-all",
    "inventory-2": "archive",
    "system-activity": "pulse",
    "schedule": "clock",
    "groups": "people",
    "description": "text-description",
    "book-open": "book-open",
    "account-tree": "organization",
    "control-point-duplicate": "copy-add",
    "fact-check": "clipboard-task",
    "text-fields": "text-font",
    "attachments-editor": "attach",
    "create-article": "document-add",
    "code-block": "code-block",
    "small-text": "text-font-size",
    "format-quote": "text-quote"
  },
  "fluent-filled": {
    "commit-queue": "cloud-arrow-up",
    "view-kanban": "grid-kanban",
    "task-alt": "clipboard-task",
    "settings-suggest": "settings-cog-multiple",
    "dashboard-customize": "grid-dots",
    "dynamic-feed": "timeline",
    "sync": "arrow-sync",
    "check-circle": "checkmark-circle",
    "tab": "tab-desktop",
    "dns": "server",
    "desktop": "desktop",
    "delete-sweep": "broom",
    "priority-high": "important",
    "warning": "warning",
    "info": "info",
    "notifications": "alert",
    "open-in-full": "arrow-expand",
    "window-restore": "window",
    "activity-feed": "history",
    "task": "clipboard-task",
    "notes": "note",
    "snapshot": "camera",
    "select-all": "select-all",
    "inventory-2": "archive",
    "system-activity": "pulse",
    "schedule": "clock",
    "groups": "people",
    "description": "text-description",
    "book-open": "book-open",
    "account-tree": "organization",
    "control-point-duplicate": "copy-add",
    "fact-check": "clipboard-task",
    "text-fields": "text-font",
    "attachments-editor": "attach",
    "create-article": "document-add",
    "code-block": "code-block",
    "small-text": "text-font-size",
    "format-quote": "text-quote"
  }
}
for (const pack of Object.keys(activityAliases)) Object.assign(activityAliases[pack], {
  hierarchy: pack === 'material-design' ? 'file-tree' : pack.startsWith('fontawesome') ? 'sitemap' : 'organization',
  hub: pack.startsWith('fontawesome') ? 'network-wired' : 'hub',
  'grid-view': pack === 'material-design' ? 'view-grid' : pack.startsWith('fontawesome') ? 'th' : 'grid',
  person: pack === 'material-design' ? 'account' : pack.startsWith('fontawesome') ? 'user' : 'person',
  'person-add': pack === 'material-design' ? 'account-plus' : pack.startsWith('fontawesome') ? 'user-plus' : 'person-add',
  process: pack.startsWith('fluent') ? 'flow' : 'cogs',
  status: pack === 'material-design' ? 'circle-double' : pack.startsWith('fontawesome') ? 'dot-circle' : 'circle',
  milestone: 'flag',
  workspaces: 'briefcase',
  'admin-panel-settings': pack === 'material-design' ? 'shield-account' : pack.startsWith('fontawesome') ? 'user-shield' : 'person-shield',
  'ungroup-items': pack.startsWith('fontawesome') ? 'object-ungroup' : 'ungroup',
  'sidebar-separator': pack === 'material-design' ? 'drag-horizontal' : pack.startsWith('fontawesome') ? 'grip-lines' : 'drag',
  'zoom-in': pack === 'material-design' ? 'magnify-plus' : pack.startsWith('fontawesome') ? 'search-plus' : 'zoom-in',
  'zoom-out': pack === 'material-design' ? 'magnify-minus' : pack.startsWith('fontawesome') ? 'search-minus' : 'zoom-out',
  'fit-width': pack === 'material-design' ? 'arrow-expand-horizontal' : pack.startsWith('fontawesome') ? 'arrows-alt-h' : 'arrow-autofit-width',
  tasks: pack === 'material-design' ? 'clipboard-text' : pack.startsWith('fontawesome') ? 'tasks' : 'clipboard-task-list-ltr',
})
for (const [pack, aliases] of Object.entries(activityAliases)) {
  Object.assign(aliases, pack === 'material-design'
    ? {'content-cut':'content-cut','content-paste':'content-paste','open-in-new':'open-in-new'}
    : pack.startsWith('fluent-')
      ? {'content-cut':'cut','content-paste':'clipboard-paste','open-in-new':'open'}
      : {'content-cut':'cut','content-paste':'paste','open-in-new':'external-link-alt'})
  for (const [name, glyph] of Object.entries(aliases)) {
    const family = iconMaps[pack][glyph] ? pack : pack === 'fontawesome-outline' ? 'fontawesome-solid' : 'material-design'
    const code = iconMaps[family]?.[glyph] || materialMap[activityAliases['material-design'][name]]
    if (code) icons[pack][name] = [iconMaps[family]?.[glyph] ? family : 'material-design', iconCode(code)]
  }
}
export function resolveIcon(name, pack) {
  if (!name) return undefined
  const separator = name.indexOf(':')
  if (separator > 0) {
    const family = name.slice(0, separator), code = iconMaps[family]?.[name.slice(separator + 1)]
    return code ? [family, iconCode(code)] : undefined
  }
  const match = /^(FA|FAS|FAR|MDI)_(.+)$/i.exec(name)
  if (!match && icons[pack]?.[name]) return icons[pack][name]
  const glyph = match ? match[2].replaceAll('_', '-').toLowerCase() : name === 'play-arrow' ? 'play' : name
  const requested = match ? (match[1].toUpperCase() === 'MDI' ? 'material-design' : match[1].toUpperCase() === 'FAR' ? 'fontawesome-outline' : 'fontawesome-solid') : pack
  for (const family of [...new Set([requested, 'material-design', 'fontawesome-solid', 'fontawesome-outline'])]) {
    const code = iconMaps[family]?.[glyph]
    if (code) return [family, iconCode(code)]
  }
  return undefined
}
