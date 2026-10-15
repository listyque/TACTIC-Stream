# Source map 0.17

Baseline: TACTIC_5_Vue_Source_Fork_0.16.zip; SHA-256 2cabd11b6022c6cabf6e4f6084cbe2dee52923d741e1dee415af91121263aa68.

| Source behavior | New implementation | Preserved / limit |
|---|---|---|
| startup/security_wdg.py: SecurityWdg and six matrix classes | ui_api/security_service.py + SecurityMatrix.vue | Same models, row families and callbacks; explicit rule editor, not full effective user evaluator. Deny/conditional/ambiguous scopes are read-only. |
| Original SecurityBuilder, six security callbacks, UserSecurityCbk, GroupAssignCbk | core/admin_commands_017.py; old paths re-export | Ten class AST hashes (including ColumnEditCbk) verified by source-provenance-017.json. No client-chosen dynamic command class. |
| GearMenuSecurityWdg.get_all_menu_names | core/security_menu_names.json | Literal source catalog; validated against original source AST. |
| UserConfigWdg, UserPanelWdg, GroupAssignWdg, SecurityGroupListWdg | UserManager.vue, UserGroups.vue, AdminWorkspace | Stock Users/Group Assignment/Group Security composition; real configured user/group tables and original membership commands. |
| SearchTypeToolWdg, ColumnEditWdg/ColumnEditCbk | SearchTypes.vue + SearchTypeService | Real registry/columns/views. Existing local metadata plus add-only columns via original ColumnEditCbk/ColumnAddCmd. No rename/delete/type mutation. |
| SideBarConfig/SideBarBookmarkMenuWdg, original widget_config model | SidebarEditor.vue + SidebarService + core/sidebar_edits.py | Per-view loss-preserving local references, new folders, original storage. Remove reference not shared definition. Not all arbitrary legacy edit callbacks. |
| App/WidgetHost original target dispatch | Existing dispatchers extended on both paths | Explicit known original handler aliases, no basename mapping of untrusted plugins. Original global Users and project UserPanel remain distinct. |
| Existing original native request lifecycle and cluster | Four finite configuration operation routes | Native admin checks/target checks/revisions/write gate/Command transactions; GET added to cluster read allowlist, writes remain primary. |
| Original action log 0.16 | New finite event labels + execute_traced | Logs original command classes and counts, not XML rules, field values or passwords. |

## Found and fixed during live comparison

- Original ProcessSecurityCbk writes `pipeline="*"` even for the project-scoped `process="*"` row. The new rule matcher initially omitted this attribute; real HTTP round-trip exposed it. Matcher and regression corrected; original callback left unchanged.
- UserSecurityCbk toggles group membership rather than assigning an explicit boolean. No-op submitted values are removed before invoking it, preventing an unchanged cell from accidentally removing a membership.
- LoginGroup has a stable generated login_group/code distinct from its human `name`. Tests and labels now preserve this separation rather than renaming or guessing the underlying key.

- New project UserPanel state persistence exposed an existing `ProdSetting.get_by_key` empty-site push/pop. Both operations are now conditional on a named site; four tests execute the actual source method for empty/named/error/admin paths.
- Detailed group assignment deliberately displays the complete registered group list so submitting the full original GroupAssignCbk payload does not silently delete out-of-project memberships; the matrix retains its original project group scope.

## Not claimed

This covers named administration mechanisms, not all 1351 inventory candidates or arbitrary Python/JS widgets. Non-admin access, cross-project effective rules, identity provider administration, destructive schema changes, arbitrary sidebar callbacks and every original drag/drop workflow remain outside this iteration.
