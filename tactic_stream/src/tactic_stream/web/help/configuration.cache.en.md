---
group: Configuration
icon: settings
order: 36
---
# Cache configuration

> Browser workspace state is stored separately from authenticated server records.

Remember process expansion controls restoration/saving of expanded objects, processes and versions in `resultState` of saved search tabs. Turning it off leaves search tabs, filters, selection and dock layouts intact but does not restore expanded branches on later loads. Existing live branches need not immediately collapse when this preference changes.

Clear cache confirms and refreshes projects, Search Types, navigation and active search results through the same native request owners used by Reload Cache. Current tab layout, preferences, selection and scroll are retained. Errors are reported; an unsuccessful refresh is not announced as success.

Clear tabs cache separately collapses object/process/version branches and clears that saved expansion state. Search tabs, filters, selection and dock layout remain intact. A failed browser save restores the previous expansion state.

Authenticated records stay in session memory, not the preference store. The desktop's persistent project/object/snapshot/relation/task/note/file/user disk caches are not implemented as browser switches. This page explicitly describes that boundary rather than rendering controls without an effect. Task/message refresh continues through its own native feature owners.

Owners: preferences.cache, workspace.js/readWorkspace/saveWorkspace and App.reloadCache. Corrupt saved state is normalized; explicit account/project state still has priority over defaults.
