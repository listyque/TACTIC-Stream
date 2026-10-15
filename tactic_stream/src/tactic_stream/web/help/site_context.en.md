---
group: Guide
icon: code
order: 92
---
# Internal structure: the Site context

> The original default Site provider, its expression context and its limits. Named sites and custom providers still require native database isolation and routing.

## Site, project and browser address

`Site` describes an installation context. It is different from a project, the current user's identity and the browser hostname. Selecting `cg_test` does not make `Site.code` equal to `cg_test`.

The supported context is the original unnamed installation: its code is an empty string. The provider is exported from `pyasm.security`; its implementation lives in `pyasm/security/security.py`. It supplies the original virtual search type and the `admin` project identity, without creating a database row or table.

```python
from pyasm.security import Site
from pyasm.biz import ExpressionParser

site = Site.get()
site.get_value('code')                       # ''
Site.get_site()                             # ''
ExpressionParser().eval('@GET(site.code)')   # ['']
ExpressionParser().eval('@GET(site.code)', single=True)  # ''
Site.get_site_data('')                      # {}
```

Unknown provider fields return `None`. This provider is not an ordinary persistent SObject; do not fetch or save it as a database record. The native `get_id()` value `-1` exists only for expression-cache identity. It fixes an original failure in `@GET(site.code)` when the code is empty; it is not a stored record id.

## Expressions, scripts and transport

The same provider works in the expression `site` context, as an initial object, as an explicit environment object, and in Naming templates. The existing API checks nested access to `sthpw/virtual` before evaluating the context.

```python
# Original XML-RPC client
server.eval('@GET(site.code)')   # ['']

# Server Python
from pyasm.security import Site
result = {'site_code': Site.get().get_value('code')}
```

Local `@SOBJECT(site)` returns Site provider instances. API `eval('@SOBJECT(site)')` explicitly refuses transporting them as records: the original XML-RPC representation was an unstable Python object address. Read fields with `@GET`, or return ordinary dictionaries from server Python. This refusal does not apply to genuine virtual SObjects such as `state` and `date`.

## Configuration and security

| Entry | Behavior in the supported default context |
| --- | --- |
| `Site.get_default_project()` / `get_user_project()` | Read `install.default_project`; do not infer the currently selected project. |
| `security.site_class` | Unset or either public base path, `pyasm.security.Site` / `pyasm.security.security.Site`. |
| `get_connect_data('')` / `get_site_data('')` | Empty dictionaries, as in the base provider. |
| Asset, web, guest and authentication hooks | Preserve the base provider's empty values; they do not choose a repository or grant guest access. |
| `build_ticket(ticket)` / `validate_ticket(ticket)` | Base extension hooks: preserve the value / return `True`. They are not authentication checks. |

Real API authentication still validates persisted tickets, owner and expiry through Security. A fake ticket does not become valid because the base provider hook returns `True`. Server Python remains limited to authorized users.

The original `get_site_data` declaration missed its classmethod decorator. Stream permits the intended class call as well as the instance call; the source failure and native correction are tested separately.

## Unsupported sites and verification

Nonempty site selection, named connections, startup, registration and custom provider factories raise `UnsupportedContract`. Stream does not silently map another site onto the current database or fall back from a broken custom provider. Named selection is rejected before changing the current Security or site stack. If it follows a database write inside a Command, the failed operation rolls that write back.

This is not complete multi-site support or custom provider integration into authentication. Old `TacticSite` HTML widgets and URL routing are outside this block. Browser project addresses are separate from the Site provider.

Thirty-seven cases compare default hooks, expressions, roots, environment objects, Naming and refusals with the actual original runtime. Original defects have separate source and native expectations. Checks also cover the unchanged XML-RPC SDK, server Python, access policy restoration, invalid tickets and rollback on SQLite and an isolated PostgreSQL database. Tests live in `tests/test_expression_site.py` and `tests/test_expression_paths.py`.

[Core model](core_model.en.md) · [Connections](connections.en.md) · [Script Editor](script_editor.en.md)
