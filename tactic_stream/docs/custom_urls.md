# Project Custom URLs

Owner: TS server, web workspace and TH native navigation. Source records are original `config/url`
(`spt_url` in the project database); plugin/template import/export preserves them.
TH resolves links to its connected server through the normal authenticated RPC
and opens native tables/layouts. Foreign HTTP origins open the system browser;
no Handler ticket is exported in an address or sent to a foreign origin.

## Page contract

The server serves the ordinary workspace at `/projects/<project>/<custom-path>`.
The browser resolves that path only after authentication through
`POST /admin/custom-url` with `{ticket, project, path, parameters}`. The selected
project comes from the path, never a `project` query parameter. Existing
`/tactic/<project>/<custom-path>` page links and `#/custom-path` fragments resolve
the same project records. This does not restore the old administration/HTML shell.

Example `config/url` record:

```xml
<!-- url: /review/{code} -->
<element>
  <display class="tactic.ui.panel.ViewPanelWdg">
    <search_type>myproject/asset</search_type>
    <search_key>myproject/asset?project=myproject&amp;code={code}</search_key>
    <view>table</view>
  </display>
</element>
```

Open `/projects/myproject/review/CAR`. A placeholder captures one nonempty path
segment, including Unicode. Literal punctuation is not a regular expression.
Exact paths precede parameterized paths; equal-specificity matches fail as
ambiguous. Retired records are ignored. DTD/entities and malformed definitions
are rejected. Parameter substitution changes option text, not XML structure or
the handler class. Path captures override query parameters; configured display
options override both, retaining original configuration ownership.

The resolver supports ViewPanelWdg/TableLayoutWdg table targets and CustomLayoutWdg
references. Table URLs use the existing view/search configuration and default to
table mode unless `view_mode` is specified. A configured search_key filters the
existing object; it must match the target Search Type/project. CustomLayout URLs
open through the existing native Frame layout command/renderer and its current
administrator/portable-markup restrictions. They do not render arbitrary HTML.

Project, URL, Search Type and object visibility checks still apply. URL access
uses the original `/tactic/<project>/<path>` rule key (and project-relative path).
Resolution does not execute imported Python classes, scripts or REST operations.
Unknown handlers fail explicitly with HTTP 501; unresolved paths are ordinary
authenticated validation errors. Opening the unauthenticated workspace shell
does not expose project configuration or grant project access.

## Authenticated REST/Python

`GET/POST/PUT/DELETE /projects/<project>/<path>` (and the original `/tactic/` path)
dispatch configured `BaseRestHandler`, `APIRestHandler` and `PythonRestHandler`
through native `CustomUrlCmd`/Command transactions. Human HTML GETs open the
ordinary workspace. REST callers authenticate with a native Bearer ticket header
or a POST body/form login_ticket, never a query ticket. Body size is limited to
1 MiB; JSON/form payloads and cross-origin requests are validated. There is no
automatic write retry. API dispatch accepts only registered public native methods;
Python retains the existing PythonCmd execution grant. A caller cannot override
the stored class or script_path. Custom Python handler imports require admin
access and a proper handler subclass. Responses are JSON, not a restored old HTML
shell. Failed commands use existing DB/FileUndo rollback.

## Portable dashboards and MCP

See [agent composition and access](admin_agent/DASHBOARDS_MCP.md) for typed native
dashboard bricks, sidebar editing and expiring project MCP access. Dashboard
publication saves ordinary config/widget_config, sidebar and config/url records;
both clients render the shared Frame. A page URL alone is never a credential or
permission grant. MCP uses a separate token and explicit selected tools. Arbitrary
legacy Python/HTML/JavaScript page rendering remains a separate compatibility gap.

Tests: `tests/test_custom_urls.py` exercises the real HTTP boundary and ACLs;
`frontend/tests/custom_urls.mjs` exercises first login, object table, reload,
legacy/fragment addresses, the existing layout renderer and missing definitions.
`test_agent_dashboards.py`, `test_agent_sidebar.py` and `test_mcp_access.py` cover
native authoring revisions, durable retries, real MCP writes, grants and revocation.
