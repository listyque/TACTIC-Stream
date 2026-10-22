---
group: Guide
icon: table
order: 93
---

# Table View and Columns Editor

The current adapted Handler Table View is ported to Stream: **45 registered names, 21 classes**. This covers current Handler scenarios, not the entire old HTML/JS runtime. Unfinished source widgets stay excluded.

## B07 checkpoint

The shared catalogue now contains **71 adapted classes / 172 named aliases** across the 104 inventory sources (30 production/3D/Maya/Flash wrappers and 3 unfinished source classes remain excluded). Geometry, menus, typed value editors, group/bottom summaries, nested `show_gear` column authoring, ordinary-user ACL, and form revision/uncertain-save checks share Frame modules. [Full cell examples and remaining explicit limits](table_widgets_b07.en.md). The following historical screenshots/counts describe the initial October 14 checkpoint.

## Table

Rounded header, 58px rows, 50px previews, 107 × 50px task cards, process note chips, relative dates, text elision and selection follow Handler. Ctrl/Shift and keyboard select rows. Double-click a row to inspect it; double-click an editable cell to use its native input. Description uses a text panel. Enter or leaving the field commits the full text; Escape cancels.

![TH](media/handler-table-th-dark.png)

![Stream](media/handler-table-stream-dark.png)

Header menu: sorting, grouping/ungrouping, display/input definition, hide, order and row height. Drag column boundaries or use arrows in 8/16px steps. Auto Fit fits widths. The columns button selects saved views or saves a new one. All use config/widget_config, without another store. Long results are virtualized; server cells are read in batches of at most 500 objects.

## Edits and tasks

Inputs resolve through edit/edit_definition and the real action.column. Assets Category therefore edits assets_category_code. Batch edits validate every revision before the first EditCmd; failure rolls back the entire batch. ID/code/project/timestamp/login and read_only are protected. Conflicts retain drafts; unknown save outcomes are checked before retrying. A ticket/project change blocks writes from the old draft.

Task cards use compact status/user editors and a separate dates panel. Selected task changes remain pending until Save task changes. Hover reveals all cards; hovering a selected row previews every selected row. Touch pins previews; Escape/outside click/scroll closes them. The count icon opens Task Manager/Inspector.

An unset status displays Select status as a hint; choose a task status from the list. Changing language does not itself modify the task.

The preview retains the full card height. When all tasks fit, no scrollbars appear; narrow windows use horizontal scrolling only. Press inside an open preview to pin it; scrolling its own card strip keeps it open.

![TH task preview](media/handler-task-preview-th-dark.png)

![Stream task preview](media/handler-task-preview-stream-dark.png)

## Columns Editor

Saved definitions, Search Type filter and search are on the left. Wizard/XML are on the right. Wizard changes title, hidden, width and display widget; the requested table column is selected immediately. Splitters adapt to width. Unknown options, other elements and comments remain in XML. Save to server updates the original record with revision validation; Discard restores stored XML.

![TH editor](media/handler-columns-editor-th-dark.png)

![Stream editor](media/handler-columns-editor-stream-dark.png)

## Adapted working classes

### Values

- `SimpleTableElementWdg`
- `RawTableElementWdg`
- `FormatElementWdg`
- `ArrayTableElementWdg`
- `XmlWdg`
- `JsonElementWdg`
- `SnapshotVersionElementWdg`

### Expressions and links

- `ExpressionElementWdg`
- `ExpressionValueElementWdg`
- `LinkElementWdg`

### Preview and collaboration

- `ThumbWdg`
- `DiscussionElementWdg`
- `TaskElementWdg`
- `TaskCompletionWdg`

### Actions

- `SObjectDetailElementWdg`
- `CheckinButtonElementWdg`
- `ExplorerElementWdg`
- `ExplorerTableElementWdg`
- `SObjectFilesElementWdg`
- `MetadataElementWdg`
- `DeleteElementWdg`

## Action examples

Add each element to an existing table; do not replace the whole config. Value, XML/JSON, expression and completion examples are in the [catalog](table_widget_examples.en.md). All class aliases are listed in reports/table-view-2026-10-14/handler-widget-checklist.json.

### SObjectDetailElementWdg

Details opens the object inspector. use_parent selects the native parent.

```xml
<element name="detail" width="64">
  <display class="tactic.ui.table.SObjectDetailElementWdg"></display>
</element>
```

### CheckinButtonElementWdg

Check-in preserves the native target, process and context and opens the Drop Plate dock. Browser files are uploaded to the server.

```xml
<element name="general_checkin" width="64">
  <display class="tactic.ui.table.CheckinButtonElementWdg"><process>publish</process><mode>upload</mode></display>
</element>
```

### ExplorerElementWdg

Explorer resolves a native sandbox/repository path and copies it. Opening a client folder requires the separately excluded desktop bridge.

```xml
<element name="folder" width="64">
  <display class="tactic.ui.table.ExplorerElementWdg"><mode>repository</mode></display>
</element>
```

### SObjectFilesElementWdg

Files opens the object inspector with existing file and preview operations.

```xml
<element name="files" width="64">
  <display class="tactic.ui.table.SObjectFilesElementWdg"></display>
</element>
```

### MetadataElementWdg

Metadata opens the existing inspector; native metadata actions remain authoritative.

```xml
<element name="metadata" width="64">
  <display class="tactic.ui.table.MetadataElementWdg"></display>
</element>
```

### DeleteElementWdg

Delete opens the native object deletion confirmation; it never deletes on the first cell click.

```xml
<element name="delete" width="64">
  <display class="tactic.ui.table.DeleteElementWdg"></display>
</element>
```

## Validation and limits

Paired captures use current Handler QML and Stream Vue, one temporary CG project, EN, MD3 dark/light, Segoe UI, 1496 × 660, DPI 96/scale 1. Native commands separately validate data and writes. Captures use isolated display controllers and do not prove a user server session. HTTP, XML-RPC, revisions, rollback and admin-only behavior have separate tests. Qt and Chromium font rasterization differs. Physical phones, other DPI and other database engines were not checked in this run.

Browser check-in uploads files to the server. Local DCC/folders and desktop move/link transfers are not available in the browser. XML/JSON remain structured display, as in current Handler. Arbitrary JS/HTML actions and old totals are outside this port.
