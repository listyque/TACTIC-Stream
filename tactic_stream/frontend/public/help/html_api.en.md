---
group: Guide
icon: code
order: 92
---
# Native HTML and server JavaScript API

Since 0.112.39 the five previously missing entry points are callable. The API catalog now has 127 available methods and two exclusions. This is entry-point coverage, **not complete behavior parity**. Vue panels remain the browser interface; native HTML is a separate SDK contract.

Further migration of the full old HTML shell/table and grouped/hierarchical HTML is excluded by user decision on 2026-10-11. Existing working methods and their common dependencies are retained. Native XML metadata and server JavaScript remain part of the supported core.

## Rendering widgets

`get_widget(class_name, args={}, values={}, libraries={}, interaction={})` returns an HTML string from a migrated `Widget` class. `args` are constructor parameters; `values` provide the request form. Calls require administrator access and run inside a native Command: writes made by a widget constructor roll back if rendering fails. Basic HTML elements, containers, tables and `BaseRefreshWdg` subclasses use the original HTML/buffer/behavior machinery.

```python
html = server.get_widget('pyasm.web.HtmlElement',
    {'type': 'span', 'child': 'Hello'})
```

This is trusted server HTML, including original behavior descriptors. Stream does not mount arbitrary old widgets inside Vue or provide the old client framework automatically. Unported classes, the interactive TableLayout shell, the old application shell and the `spt_help` library fail explicitly. `interaction` retains the source's unused argument. `libraries` registers request library metadata; it does not install missing JavaScript dependencies.

Configuration → Server configuration → Security exposes `api_widget_restricted`. It applies original `builtin` widget rules and checks bound arguments when using a `$widget_key`. Keys belong to the authenticated user and its verified ticket directory. It does not grant ordinary users permission to execute trusted HTML.

## Request palette

`set_palette(palette)` pushes a native Palette onto the current server request stack and returns `None`. Use a named palette (`DARK`, `LIGHT`, `DEFAULT`) or a color dictionary. Project/user/config defaults retain their original order. Python expressions are rejected; configuration is parsed as data.

A standalone XML-RPC call ends its request immediately; it does not persist a theme for later RPC calls. To render under a palette, use one server Python script and its local SDK:

```python
from pyasm.web import Palette
server.set_palette('DARK')
try:
    return server.get_widget('pyasm.web.DivWdg')
finally:
    Palette.pop_palette()
```

Browser appearance settings are separate. HTML buffers, palettes, WebState and JavaScript contexts belong to the current request and do not leak between concurrent requests.

## Column HTML

`get_column_widgets(ticket, search_type, search_keys, element_name)` returns a nested list: one row per object, containing the HTML `<td>` for the selected column. It uses the original table configuration, cell attributes, styling hooks, color maps and migrated column display handlers. Unsupported handlers raise an error. Metadata DTOs do not replace HTML.

The original implementation drops a first insertion key ending in `id=-1` and loads objects only when **more than one key remains**. A single key therefore returns `[]`; this behavior is retained. Missing or inaccessible requested rows cause a fault. Grouped/hierarchical HTML and the full interactive table shell remain unported.

The original Python SDK has no convenience helper for this method; call its XML-RPC proxy:

```python
cells = server.server.get_column_widgets(server.ticket,
    'cg/assets', [first_key, second_key], 'name')
```

## Application state

`set_application_state(ticket, key, panel_name, widget_class, options, values={})` supports the original `key='top_layout'`. It resolves the project's/configured `top_class_name`, updates that panel in the native XML configuration and saves user/project WidgetSettings. The result is `True`. String values and nested options are preserved; nonstring form values are skipped as in source. The native nested-options bug and missing writer creation are corrected.

```python
server.server.set_application_state(server.ticket, 'top_layout',
    'main_body', 'pyasm.web.DivWdg', {'title': 'Example'}, {})
xml = server.server.get_widget_setting(server.ticket, 'top_layout')
```

Use the proxy in this example: the original Python SDK lacks `set_application_state` and its `get_widget_setting` helper recursively calls itself. Browser dock layouts retain their own persistence; this API does not change them. Restoring an unported native widget cannot make its old HTML shell available.

## Server JavaScript

Script Editor now offers **Server JavaScript**, saved as `language='server_js'`. Script Shelf can execute these saved scripts. Browser `javascript` remains a separate execution target.

`execute_js_script(script_path, kwargs={})` uses original JsCmd/custom_script lookup. A path selects `folder/title` and takes precedence over `kwargs.code`; `file_path` is a trusted administrator-side source path. Each kwargs entry becomes a JavaScript global. Original JS SDK methods are available through `server` and use the current login, project, API rights and Command transaction.

```javascript
var note = server.insert('sthpw/note', {note: input.text});
return {key: note.__search_key__, ping: server.ping()};
```

```python
result = server.execute_js_script('', {
    'code': "return {ping: server.ping(), value: input.value};",
    'input': {'value': 7},
})
# {'status': 'OK', 'description': '...', 'info': {...}}
```

QuickJS-NG replaces obsolete PyV8 while retaining the original JavaScript SDK and command lookup. Execution is synchronous: Promise returns are rejected, as are cyclic results. No return gives `info=None`. Uncaught errors roll back API writes and identify the `tactic://project/script` source; caught API errors remain ordinary JavaScript errors. `console.log` writes to the server log.

Server JavaScript is administrator-only trusted code, not a sandbox. It has no browser DOM, DCC connection, async event loop or arbitrary PyV8 Python-object interoperability. The bridge transports JSON values; it does not supply filesystem bindings. Native `server_js` PythonTrigger callbacks use the same command and transaction.

## Verification and limits

`test_html_api` checks unchanged SDK/XML-RPC calls, rights, request isolation, rollback, saved paths, native cells and layout persistence. `test_html_parity` executes the same HTML/palette operations in the original embedded runtime and Stream. The original PyV8 runtime is not exercised; the replacement engine uses the source JS client and real native API calls. See [Core and API compatibility](help://api_compatibility) for the remaining method variants and exclusions.
