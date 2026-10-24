# Tactic Frame prototype

Tactic Frame is the shared interface layer for TACTIC Handler and TACTIC Stream.
This prototype uses one layout/behavior source and two native renderers. It does
not introduce another language or parser. `.mjs` is a standard JavaScript module;
UI descriptions are objects with named fields returned by that module. Qt and
Vue execute the same shared code and create their own engine's controls.

## Source map

| File | Responsibility |
| --- | --- |
| [gantt.json](gantt.json) | Dimensions, typography, initial window size and translations |
| [gantt.ui.mjs](gantt.ui.mjs) | Shared layers, elements, labels, colors and events |
| [gantt.state.mjs](gantt.state.mjs) | Initial state, geometry, transitions, dates, drag, zoom, Undo/Redo |
| [GanttDemo.qml](GanttDemo.qml) | Native scene rendering with Qt and Handler controls |
| [GanttDemo.vue](GanttDemo.vue) | The same scene through DOM and Stream App controls |
| [gantt_cases.json](gantt_cases.json) | Matching real-input scenarios |

Start at `scene()` in gantt.ui.mjs: toolbar, headers, date scale, groups/task rows,
overview, scrolling and footer appear in that order.

## Element description

A button from the toolbar loop:

```js
add(toolbar, "Button", button.id, {
  x: buttonX,
  y: 6,
  width: buttonWidth,
  height: 36,
  text: translate(button.text),
  action: button.action,
  enabled: button.enabled
});
```

Button names the primitive; id is stable. Coordinates are relative to its layer.
action is shared event data, not an API call or independently implemented QML/Vue
handler. Layers own x/y/width/height and nodes; renderers clip to their bounds.
Elements paint in description order: background, grid, task bar, fill, label,
handles. Overlap order is shared, like a normal QML scene or DOM.

The simple [screen.json](screen.json) form nests Row/Column. Gantt scale/bar
calculations use ordinary JavaScript; JSON does not store executable expressions.

## Native controls and boundaries

- TH QML controls: `TH/thlib/ui/qml/controls` in the independent Handler checkout.
- TS Vue controls: `TS/tactic_stream/frontend/src/controls`.

Button and CheckBox reuse house controls; Label and Rectangle use Qt/DOM rendering.
The prototype is not a complete project control catalogue and does not translate
arbitrary QML into HTML. Shared modules cannot access DOM, Qt, network or files;
their JavaScript must work in both engines. Domain controllers and TACTIC retain
persistence/authorization ownership; this demo holds changes in memory.

## Running and checking

`start_demo.cmd` opens native QML and a browser report with live Vue. Generated
report: `output/gantt-report.html`. From the Stream product directory:

```powershell
.venv/Scripts/python.exe -B -X utf8 tools/shared_ui_demo/gantt_qml.py --capture
cd frontend
$env:STREAM_BROWSER_CHANNEL='msedge'
node tests/shared_gantt_demo.mjs
node tests/shared_gantt_report.mjs
```

The harness compares paired states, actual geometry, colors/fonts, shared scene
and operation history. Text rasterization differs between Qt and Chromium.
Production screens, server persistence, large lists and mobile layouts are outside
this prototype's qualification. Follow the [shared contract](../../docs/frame/contract.md).
