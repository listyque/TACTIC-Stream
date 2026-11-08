###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Explicit XML-RPC entry points with original signatures and ticket envelopes.

Selected reads, account/business/workflow writes and preallocation/file APIs are active. Writes use native Command,
SObject persistence, triggers and the durable journal.
"""
from importlib.resources import files
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import inspect
import itertools
from io import StringIO
import json
import logging
import os
import tempfile
import time
import threading
import uuid

from pyasm.biz.project import Project
from pyasm.biz.schema import Schema
from pyasm.search.search import RequestContext, SObject, Search, SearchType, request_context
from pyasm.common.errors import AuthenticationError, SecurityException, UnsupportedContract
from pyasm.search.keys import SearchKey
from pyasm.security.authenticator import Authenticator
from pyasm.common.environment import Environment
from pyasm.common import System, Container
from tactic.core.sidebar_config import get_internal_widget_configs as _internal_widget_configs

LOG = logging.getLogger(__name__)
REQUEST_COUNT = itertools.count(1)
LAST_RSS = System().memory_usage().get('rss')
LOG_LOCK = threading.Lock()


def upload_file_name(filename):
    from pyasm.checkin.repo import _check_file_name
    if not isinstance(filename, str):
        raise ValueError('Upload filename must be a string')
    filename = os.path.basename(filename.replace('\\', '/'))
    _check_file_name(filename)
    return filename


def check_ticket_paths(paths, directory, file_range=None, check_contents=True):
    """Check actual frames too: a valid template can expand to an escaping symlink."""
    from pyasm.biz import File, FileGroup
    root = Path(directory).resolve()
    for path in paths:
        expanded = FileGroup.expand_paths(path, file_range) if file_range and File.is_file_group(path) else [path]
        if any(not Path(item).resolve().is_relative_to(root) for item in expanded):
            raise ValueError('Check-in files must remain in the ticket directory')
        for item in expanded:
            if check_contents and Path(item).is_dir():
                for parent, dirs, names in os.walk(item):
                    for name in dirs + names:
                        child = Path(parent) / name
                        if not child.resolve().is_relative_to(root):
                            raise ValueError('Check-in directory contents must remain in the ticket directory')
                        if child.is_dir() and (child.is_symlink() or child.is_junction()):
                            raise ValueError('Check-in directory links are not supported')


def log_arguments(arguments):
    """Original positional argument display, with passwords/payload secrets redacted."""
    def clean(value, depth=0):
        if depth >= 6:
            return '...'
        if isinstance(value, dict):
            return {str(key)[:100]: ('[redacted]' if sensitive(key) else clean(item, depth + 1))
                    for key, item in list(value.items())[:20]}
        if isinstance(value, (list, tuple)):
            if value and isinstance(value[0], str) and sensitive(value[0]):
                return [value[0][:100], '[redacted]']
            return [clean(item, depth + 1) for item in value[:20]]
        if isinstance(value, str):
            return value[:500]
        return value if value is None or isinstance(value, (bool, int, float)) else type(value).__name__

    def sensitive(key):
        return any(word in str(key).lower() for word in ('password', 'ticket', 'token', 'secret'))

    values = ['[redacted]' if sensitive(key) else clean(value)
              for key, value in arguments.items() if key != 'ticket']
    return values

SUPPORTED_METHODS = frozenset({
    'log', 'subscribe', 'unsubscribe', 'add_interaction', 'get_interaction_count',
    'set_widget_setting', 'get_widget_setting', 'get_plugin_dir', 'clear_upload_dir', 'fast_query',
    'set_config_definition', 'get_config_definition', 'update_config', 'add_config_element',
    'execute_cmd',
    'add_column_to_search_type', 'add_instance', 'check_access', 'class_exists', 'connect_sobjects', 'create_search_type', 'get_connected_sobject', 'get_connected_sobjects', 'get_instances', 'get_release_version', 'get_server_api_version', 'get_server_version', 'remove_instance',
    "get_ticket", "get_ticket_data", "fast_ping", "ping", "query", "get_column_info", "get_by_search_key", "get_by_code",
    "get_column_names", "get_table_info",
    "get_related_types", "get_parent", "get_all_children", "get_parent_type", "get_child_types",
    "get_types_from_instance",
    "update_multiple", "insert_multiple", "insert_update", "get_unique_sobject", "retire_sobject", "reactivate_sobject", "clone_sobject", "create_note", "get_tasks", "get_pipeline_xml", "get_pipeline_processes", "get_preference", "set_preference",
    "insert", "update", "delete_sobject", "create_task", "add_initial_tasks",
    "get_message", "get_messages", "log_message",
    "execute_python_script",
    'get_handoff_dir', 'get_paths', 'get_base_dirs', 'get_client_dir', 'get_path_from_snapshot', 'get_expanded_paths_from_snapshot', 'get_all_paths_from_snapshot', 'get_dependencies', 'get_all_dependencies', 'group_checkin', 'add_group', 'query_snapshots', 'get_snapshots_by_relative_dir', 'set_current_snapshot',
    'get_task_status_colors', 'get_input_tasks', 'get_output_tasks', 'create_pipeline', 'get_pipeline_xml_info', 'get_pipeline_processes_info', 'call_trigger', 'call_pipeline_event', 'get_pipeline_status', 'add_dependency', 'add_dependency_by_code', 'lock_sobject', 'unlock_sobject',
    "get_snapshot", "create_snapshot", "eval",
    "get_preallocated_path", "get_virtual_snapshot_path", "add_file", "remove_file", "upload_file", "get_upload_file_size", "simple_checkin",
})
WRITE_METHODS = frozenset(('execute_cmd', 'add_instance', 'remove_instance', 'create_search_type', 'add_column_to_search_type', 'connect_sobjects', 'create_pipeline', 'call_trigger', 'call_pipeline_event', 'add_dependency', 'add_dependency_by_code', 'lock_sobject', 'unlock_sobject', 'group_checkin', 'add_group', 'set_current_snapshot', 'update_multiple', 'insert_multiple', 'insert_update', 'get_unique_sobject', 'retire_sobject', 'reactivate_sobject', 'clone_sobject', 'create_note', 'set_preference', 'insert', 'update', 'delete_sobject', 'create_task', 'add_initial_tasks', 'log_message', 'execute_python_script', 'create_snapshot', 'add_file', 'remove_file', 'upload_file', 'simple_checkin'))
PROTECTED_TYPES = frozenset({"sthpw/login", "sthpw/ticket", "sthpw/login_group", "sthpw/login_in_group",
                             "sthpw/transaction_log", "sthpw/sobject_log", 'sthpw/db_resource', 'sthpw/exception_log', 'sthpw/debug_log'})
WRITE_METHODS |= frozenset(('subscribe', 'unsubscribe', 'add_interaction', 'set_widget_setting',
                           'clear_upload_dir', 'set_config_definition', 'update_config', 'add_config_element'))


SUPPORTED_METHODS |= frozenset(('generate_ticket', 'test_speed', 'test_error', 'get_connection_info',
                               'execute_class_method', 'add_queue_item', 'checkout', 'get_full_snapshot_xml', 'get_doc_link'))
WRITE_METHODS |= frozenset(('log', 'execute_class_method', 'add_queue_item', 'checkout'))
SUPPORTED_METHODS |= frozenset(('undo', 'redo', 'execute_transaction'))
WRITE_METHODS |= frozenset(('undo', 'redo', 'execute_transaction'))
SUPPORTED_METHODS |= frozenset(('start', 'finish', 'abort', 'set_state', 'set_project'))
WRITE_METHODS |= frozenset(('start', 'finish', 'abort', 'set_state', 'set_project'))
SUPPORTED_METHODS |= frozenset(('send_rest_request',))
SUPPORTED_METHODS |= frozenset(('missing_method',))
SUPPORTED_METHODS |= frozenset(('set_palette', 'get_widget', 'get_column_widgets', 'set_application_state', 'execute_js_script'))
WRITE_METHODS |= frozenset(('get_widget', 'get_column_widgets', 'set_application_state', 'execute_js_script'))
PROTECTED_TYPES |= frozenset(('sthpw/transaction_state',))

def check_record_access(base):
    if base in ('sthpw/login', 'sthpw/ticket', 'sthpw/login_group', 'sthpw/login_in_group', 'sthpw/db_resource'):
        security = Environment.get_security()
        if security is None or not security.is_admin():
            raise SecurityException('Security records require administrator access')
    elif base in PROTECTED_TYPES:
        raise UnsupportedContract('Reading journal records needs the original field/access policy')


def compatibility_manifest():
    manifest = json.loads((files("tactic_stream") / "compatibility/api_manifest.json").read_text(encoding="utf-8"))
    for method, record in manifest["methods"].items():
        if method in SUPPORTED_METHODS:
            record["status"] = "partial"
    manifest['implemented_read_scope'] = 'Owned SQLite/PostgreSQL system and registered project reads; native users/groups and literal access rules; preallocation paths and ticket upload size; Python XML-RPC'
    manifest['implemented_read_scope'] += '; 0.74 same-resource Search joins for search_type/search_code/search_id references in both directions, prefixed discriminators, actual physical table names, chained/branched joins and named-path ordering through native query/SDK. Joined types recheck Search ACL. Original SQLite database-qualified SQL, child discriminator, ignored prefixes, logical-table, branch-deduplication and named-order bugs have separate source/native expectations. Cross-resource joins remain guarded; repeated target tables retain first-join-wins, separate aliases are not introduced.'
    manifest['implemented_write_scope'] = 'Administrator configured-system accounts, business records, messages, process_state and custom scripts through native Command; saved Python execution, preallocation, binary XML-RPC upload and append/remove through the file journal, and same-transaction local SDK; Batch CRUD, clone/retire/reactivate, notes/tasks, pipeline reads and per-user/project preferences; Repository/path/snapshot queries, dependency reads/writes, snapshot locks and upload/inplace frame group check-in/append; flat pipeline creation/info, task neighbors, trigger/workflow events/status through native engine; HTTP ticket uploads/create-append and simple_checkin with original Pillow image previews is active; PDF/video, metadata, levels and handoff check-in remain unported; full Workflow, script ACLs and external-resource writes remain unported 0.104 native XML preview with original priority resolver and shared Vue renderer; bounded declarative TabWdg/ViewPanelWdg nesting. Child tables read-only, no HTML renderer, TSQL/state/actions, full controls or dependency snapshot. 0.105 native child ViewPanel filter/sort/offset paging and literal legacy options through unchanged query; per-tab state, read-only data, no advanced SearchWdg or child CRUD.'
    manifest['implemented_write_scope'] += '; 0.50 connections, schema-defined instances and search-type/table/column creation on the configured system resource, generic registered SObjects and global search indexing through the same administrator Command; table/alter journals and transactional DDL. Durable schema undo/redo remains unported'
    manifest['implemented_write_scope'] += '; 0.51 administrator execute_cmd and original CreateProjectCmd simple-project lifecycle: exclusive SQLite/PostgreSQL database creation, original empty configuration tables and adopted migrations, initial search types and compensating cleanup before system publication. Distributed/crash recovery, non-simple base schemas remain unported. Command keys, renderer values and nontransactional API commands are refused.'
    manifest['implemented_write_scope'] += '; 0.52 existing registered project databases on the configured SQLite/PostgreSQL endpoint join administrator SObject CRUD and schema DDL, native triggers, global index and system journal. Ordinary pre-commit failures roll back all joined databases. Original sequential per-database commit semantics retained, with the system journal last; PartialCommitException explicitly reports a later failure after an existing database committed. Files and command rollback hooks are retained after partial commit, requiring inspection before retry. No distributed atomicity is claimed. External project resources and multiple connections to one physical database remain guarded.'
    manifest["implemented_methods"] = sorted(SUPPORTED_METHODS)
    manifest['implemented_write_scope'] += '; 0.53 backend PluginInstaller/PluginTools directory and ZIP manifest/SPT imports, registry/table/schema creation, unique object updates, nested plugins/includes/trusted Python and config/plugin registration; native ProjectTemplateInstallerCmd creates simple projects or imports into registered projects. Administrator Command security, file rollback and owned DB cleanup on SQLite/PostgreSQL. No new XML-RPC methods; installer is independent of transport. Export/uninstall, SQL views, other unported config types and arbitrary real package compatibility remain unfinished.'
    manifest['implemented_write_scope'] += '; 0.54 backend WidgetDbConfig/WidgetDbConfigCache, ProjectSetting and original deprecated pyasm.prod.biz.ProdSetting; config/widget_config, prod_setting, trigger and client_trigger imports with source schema migrations on SQLite/PostgreSQL. XML view/element edits and priority merge, setting writes and same-process project triggers; write/delete/rollback/project-switch cache invalidation. Legacy renderer, executable Mako, default widget views and remaining config types remain guarded. No new XML-RPC methods.'
    manifest['implemented_write_scope'] += '; 0.55 original project pipeline/default/process dependencies, custom-property metadata and transactional column deletion, ingest rule/session and translation definitions; automatic captured schema/registry bootstrap and per-project installer upgrade. No ingest engine, frontend translation bridge or new XML-RPC methods. Existing admin/renderer/workflow/distributed-commit limits remain.'
    manifest['implemented_write_scope'] += '; 0.56 original backend PluginCreator and PluginTools SPT export, TableDataDumper/TableSchemaDumper, manifest/ZIP registration, include/Python files, variable/relative-directory options and id/ignore handling. SQLite/PostgreSQL portable id/columns/NOT NULL/UNIQUE metadata and same-project/other-project import checked. Source string corruption and missing empty files fixed; exports use the existing admin Command/FileUndo boundary. Uninstall, nested plugin export, full database backup/defaults/CHECK/nonunique indexes, SQL views/foreign/exclusion/partial/expression indexes and raw SQL data dumps remain unfinished. No new XML-RPC methods.'
    manifest['implemented_write_scope'] += '; 0.57 original backend PluginUninstaller node reversal, SObject deletion, nested plugins/includes/Python undo_path, plugin-content cleanup/deregistration and PluginTools.remove_search_type; native DropTable schema cache/transaction. Common registry/schema definitions and package directories remain, remaining rows backed up with original IDs and explicit NULLs, reinstallation repairs sequences. Persisted administrator Command, no swallowed deletion errors/CASCADE, file/DDL rollback and dependent view/FK refusal on both vendors. Pipeline selection follows imported project prefix; successful SPT force-insert flags reset and previous SQL query results survive nested metadata reads. Portable schema limits and durable schema undo/redo remain; ZIP uninstall requires an installed directory. No new XML-RPC methods.'
    manifest['implemented_write_scope'] += '; 0.59 original ProjectTemplateCreatorCmd whole-project manifest/SPT/ZIP export and get_zip_path; original public names/signatures, own-project plus base-type namespaces, read-only sequence floors and SQLite import floor restoration. Same backend installer copies exported simple-project schemas/config/scripts/groups/pipelines/notification metadata into a fresh SQLite/PostgreSQL database, with admin Command/file rollback. Notification metadata writes invalidate definition/event caches; email execution remains guarded. Templates export structure/config, not asset records or repository files. Existing portable-schema, non-simple project, renderer, updater and durable undo limits remain. No new XML-RPC methods.'
    manifest['implemented_write_scope'] += '; 0.60 adds 13 partial XML-RPC methods for subscriptions/interactions, WidgetSettings, plugin paths, upload cleanup, optional administrator fast_query and XML config definition/edit/reorder. Original WidgetSettings/Subscription classes and captured system tables/default XML metadata; request cache invalidation, persisted-admin Command/file rollback on SQLite/PostgreSQL. Fixes project/login isolation, separator selection, XML escaping/node import and caller input mutation. Fast query preserves Security. Default license management metadata excluded. Legacy renderer, deprecated form reads, unsupported base/view modes and ExceptionLog persistence remain unported. Original ProjectTemplateUpdaterCmd is empty and explicitly refused; use existing installer for explicit imports.'
    manifest['implemented_write_scope'] += '; 0.61 nine partial methods: random key generation, administrator ticket/connection diagnostics, deliberate test_error, trusted class-method execution, queue insertion, checkout, full snapshot XML and documentation aliases. Original Queue pending conditional claim/add class and captured schema/registry/column migrations/state index, persistent-admin Command, cache refresh/priority-zero fixes and two-consumer check on SQLite/PostgreSQL. Queue runner/scheduler/crash recovery remain unported. Original checkout path/lock selection and both callbacks enabled; levels guarded. Full snapshot XML copies source XML and handles quoted filenames; remote web URLs follow request-local HTTP origin. Native connection counts describe only the current request. Original Url class uses urllib.parse with corrected repeated option encoding; WebState renderer excluded. Durable undo/redo, resumed API transactions and sync replay still unported.'
    manifest['implemented_write_scope'] += '; 0.63 durable exception/debug journals and original log API; administrator access, independent local Command connection, active system writer/email guards; top-level rollback/commit failures log without changing original errors. Remote transaction replay and full diagnostics inside system writes remain unfinished.'
    manifest['implemented_write_scope'] += '; 0.64 original inline/file/saved PythonCmd execution and packaged XML WidgetConfig/View metadata; Mako retained with source-line diagnostics. 0.65 local query returns native SObjects on request or native dictionaries otherwise, with original empty/single behavior. Original record conversion exposed to local SDK, shared with transport records: datetime/Decimal strings, unchanged stored metadata, corrected projection/use_id/mixed-type keys. Same-request/security/Command boundaries retained. Unchanged Handler object/snapshot/file hydration exercised. No additional public XML-RPC methods or full renderer compatibility claimed.'
    manifest['implemented_write_scope'] += '; 0.66 adds partial undo/redo/execute_transaction via original UndoCmd/RedoCmd, SObjectUndo and RunTransactionCmd. SObject insert/update/delete replay, idempotent transferred journals and XML input run inside persisted-admin Command with rollback. Fixes Python 3 dict detection, premature raw XML log insertion, timestamp tie selection, timezone comparison, stale request identity on replay and original code-renaming object state. Original Milestone class, shipped table/registry and project default enabled at install/upgrade. Durable file/schema/multi-site replay, remote sync and resumed transaction tickets remain guarded.'
    manifest['implemented_write_scope'] += '; 0.67 client transaction lifecycle: original start/finish/abort, set_state/set_project, TransactionState and Transaction.resume/resume_by_id. One durable XML/zlib journal across requests; ordinary changes still commit per request, with grouped undo rather than an open database transaction. Ticket owner/expiry, active-ticket reset refusal, closed-ticket race checks and native ticket locking on SQLite/PostgreSQL. XML-RPC and HTTP uploads join the journal. Durable file undo/redo compensates completed/partial IO on later failures, preserves copied bytes and upload-to-repository dependencies. Source repeated-state and XML append bugs fixed. Fresh install/upgrade captures the original state schema/registry. Schema, multi-site, remote sync, arbitrary cross-ticket HTTP upload and historical versionless journals without backups remain guarded; full API/UI compatibility is not claimed.'
    manifest['implemented_write_scope'] += '; 0.68 ordinary local table create/drop and column add/drop replay through existing undo/redo/execute_transaction. Original TableUndo/TableDropUndo/AlterTableUndo names and directions retained; native vendor snapshots preserve rows, defaults, nullability, constraints, indexes, triggers and standard ID floors. New rows receive restored native defaults; unrelated cells stay current. Changed remaining schemas refuse restoration. DDL joins existing Command rollback. Source API add_column missing journal and string-resource log_add bugs fixed. Original runtime value-loss/API-journal differences explicitly tested; unmodified source SDK exercised over XML-RPC. Special tables, column type modification, cross-vendor/historical incomplete journals and multi-site replay remain guarded. No additional exposed methods or full compatibility claim.'
    manifest['implemented_write_scope'] += '; 0.69 send_rest_request uses stdlib HTTP(S), source GET/POST/form/JSON semantics including error-status JSON; administrator access, URL credentials unsupported. Explicit schema upgrades include registered local project configuration. Deprecated production objects, production schemas and commit_session excluded by user scope.'
    manifest['implemented_write_scope'] += '; 0.70 level check-in/read/checkout, full XML, versionless reads and metadata merge/replace for original snapshot and CRUD methods. Parent-level/string-version/process/ref-table defects fixed explicitly. Level-scoped versionless aliases, handoff/context indexing/parsers remain unported. Deprecated pyasm.prod package and imports removed by user scope; API implementation now pyasm.web.api_xmlrpc, settings use pyasm.biz.ProjectSetting. Unused SnapshotType/FileAccess classes and lookup tables excluded; snapshot_type field, TransactionState and interaction APIs retained. No additional public methods.'
    manifest['implemented_write_scope'] += '; 0.74 relationship joins and named order paths use native Search. 0.75 context_index_padding and original metadata parser classes/hook enabled through existing check-in APIs and source migrations. 0.76 handoff simple/append/group APIs use original client/server path configuration and per-ticket directories, shared actual-file containment checks and existing Command/FileUndo semantics. SQLite/PostgreSQL and unchanged XML-RPC SDK checked on private fixtures. Custom check-in classes, ingest/pipeline listeners, privileged ownership and specialized media/group metadata remain unported; no full API parity claim.'
    manifest['implemented_write_scope'] += '; 0.77 original Command dependent Pipeline actions and task approval enabled, including deferred checkin/move and trusted custom BaseCheckin classes through simple_checkin and current-scope FileCheckin.get. Caller commits before dependent actions, as in source; failed deferred action writes roll back instead of the original swallowed-error commit. System type aliases and full-key identity lookup corrected with separately recorded fresh-source differences. Ingest, remaining Workflow node handlers, privileged ownership and specialized media remain unported.'
    manifest['implemented_write_scope'] += '; 0.78 file ingest through original IngestionCmd/CheckinRule commands, saved rules/sessions, rule/list scan, validation/process scripts and stock SDK check-in; delayed File/Snapshot ingest persistence enabled. Original defects fixed explicitly, request-local serializable reports. SQLite/PostgreSQL and unchanged XML-RPC SDK checked. Directory publication, script scan, experimental ingestX and remaining Workflow branches unported; no full parity claim.'
    manifest['implemented_write_scope'] += '; 0.79 original directory File/check-in and Common/FormatValue/TimeCode dependencies enabled; directory rule/list ingest uses core copy without deleting unrelated handoff. Stock XML-RPC directory_checkin and shallow expanded paths verified, nested ticket links checked before IO. Source bugs fixed explicitly; SQLite/PostgreSQL and rollback checked. Script scan, ingestX, privileged ownership and remaining Workflow branches remain unported; no full parity claim.'
    manifest['implemented_write_scope'] += '; 0.80 original Workflow condition/progress/hierarchy/input/output handlers enabled through the existing events and XML-RPC call_pipeline_event. Nested task generation and caller stacks retain shared SObjects/Command/Trigger; child states are scoped by full process path. Source duplicate completion, cross-pipeline condition lookup, lost context, ambiguous output parent and premature hierarchy completion corrected. Cyclic/missing hierarchy rejected before effects; duplicate task generation preserves child policy and full contexts. Original runtime, SQLite/PostgreSQL and unchanged XML-RPC SDK checked. Related/dependency execution, worker-wide startup/CoreInit, custom node handlers and server JavaScript remain unported; no full parity claim.'
    manifest['implemented_write_scope'] += '; 0.81 original cross-object Workflow dependencies and terminal notifications enabled, including v1/v2/XML settings, waiting/nonwaiting, multiple durable callers, revise/reject and callback context. Same-object alternate graphs remain guarded. Worker lifespan calls native CoreInit once: global StatusLog, DisplayName, Workflow events and Snapshot integral triggers. Request registration avoids duplicates. StatusLog uses immutable commit input after nested triggers; logical project scopes retained for user SearchTypes in shared physical databases. Workflow writes are transaction-serialized on SQLite/PostgreSQL; process state is text with an owned PostgreSQL upgrade. Source defects asserted separately; unchanged SDK across fresh HTTP requests, concurrency and rollback checked. Custom node configurations, server JS and generic ProcessStatusTrigger remain unported; no full parity claim.'
    manifest['implemented_write_scope'] += '; 0.82 original PipelineSaveCbk, ProcessInfoCmd/NewProcessInfoCmd and trigger-folder constants adopted as headless modules. Original tactic.ui.tools and pipeline_wdg command paths import the same classes without HTML. execute_cmd persists v1/v2 process properties, saved Python scripts/trigger bindings, hierarchy/status/dependency/progress settings and process-code XML; source double escaping, malformed settings swallowing, missing saved-path binding, wait=False and stale config caches corrected. Workflow custom process/save/delete handlers resolve from existing widget_config with persisted-admin/Command checks and strict backend base classes; constructor/save failures propagate once and roll back. ProcessStatusTrigger consumes process completion events scoped to the configured parent pipeline, waits for related inputs, and carries callback context. Config triggers load for admin/sthpw projects too. Source-runtime, stock SDK fresh requests, SQLite/PostgreSQL, rollback/cache/security checked. HTML node/info handlers, rename/reference migration, same-object alternative dependencies and JS remain unported; no full parity claim.'
    manifest['implemented_write_scope'] += '; 0.83 original PipelinePropertyCbk/PipelineSaveCmd and Pipeline save_version/set_to_latest/set_to_versionless enabled through existing commands and script API. Related clones reuse SObject relationships; version processes, action/progress triggers, saved project scripts, XML identifiers and metadata references remapped. Version numbering uses existing SQLite/PostgreSQL workflow transaction lock. Original process template inheritance enabled with exact owner lookup, insert recursion and identity inheritance fixes; callback retains applied template graph. Default computation errors propagate and roll back. Actual source runtime, stock XML-RPC SDK, SQLite/PostgreSQL, rollback and concurrent version saves checked. Version copies retain referenced subpipeline/dependency graphs and external class code; not a complete immutable project revision. HTML, process rename/reference migration, same-object alternate dependencies and JS remain unported; no full parity claim.'
    manifest['implemented_write_scope'] += '; 0.84 original Workflow dependency flow supports alternate pipelines on the same SObject, with isolated process/overall state, messages, packages, callbacks and namespaced tasks. Primary process names/message/API formats remain unchanged; alternate roots use pipeline_code::process and existing process_state.pipeline_code. Target-state reads use target graph context; original object overall-status shortcut applies only to its primary graph. Task generation and status events route flat/nested alternate graphs and retain qualified duplicate/context keys. Existing call_pipeline_event accepts the explicit qualified name with unchanged signature; get_pipeline_status reads the matching original message key. Source same-object recursion is documented as corrected behavior. Actual source runtime, stock SDK fresh requests, SQLite/PostgreSQL, legacy unscoped state adoption, hierarchy, cycle and rollback checks passed. HTML, process rename/reference migration, server JS and remaining Workflow/package branches remain unported; no full parity claim.'
    manifest['implemented_write_scope'] += ' 0.85 shared workflow process deletion: original editor save/dependency path and direct SObject/XML-RPC delete_sobject invoke CustomProcessConfig delete once before removal, retaining deleted node type across graph reload. Owned action/progress triggers are removed transactionally; shared references reject deletion, external listeners/scripts/tasks/history and independent saved versions survive. Source deleted-node/exception swallowing defects corrected. Direct definition delete retains original XML contract; whole-pipeline deletion and node rename/type migrations remain unverified.'
    manifest['implemented_write_scope'] += ' 0.86 shared Pipeline type changes clear old custom/action/progress bindings and hierarchy settings even without editor settings, retain process identities/tasks/scripts/history and independent versions, and apply new editor settings through original commands. Existing XML-RPC update/execute_cmd contracts unchanged. Actual source stale-binding defects documented; handler/late rollback and stock SDK new action execution checked. Running instance state and node rename migrations remain unsupported.'
    manifest['implemented_write_scope'] += ' 0.87 original built-in Workflow snapshot/message output packages use qualified process scope; Final/latest/fallback selection retained and arbitrary input packages preserved. Stock XML-RPC task updates carry nested snapshot results into downstream action and persisted state; late failure rolls back tasks/messages/state/notes/snapshot rows. Existing API signatures and snapshot context defaults unchanged. Source cross-process selection corrected, dead custom generator fragments removed; arbitrary packagers and snapshot namespace migration remain unverified.'
    manifest['implemented_write_scope'] += ' 0.88 original TaskAutoSchedule even/even_day/from_end_date, configured add_initial_tasks and dependent task rescheduling enabled over native Command/SObject. Explicit mode overrides project/XML defaults; invalid/missing/reversed dates fail, caller-owned commits and rollback retained, visited dependencies isolated per request. Original runtime valid contracts/explicit argument bug, stock XML-RPC generation and SQLite/PostgreSQL checked. schedule/mode catalogued read-only with EN/RU labels; no work calendars, automatic date-update cascade or new API methods.'
    manifest['implemented_write_scope'] += ' 0.89 original custom task status pipelines enabled through Task generation, shared SObject.commit and existing update/execute_cmd APIs. v1/v2/XML mapping, multi-task completion, hierarchy/alternate status context and neighbor payloads retained; In Progress dispatch, XML completion lookup and saved input restoration fixed. Missing graphs, unknown mappings and cyclic custom transitions fail with transaction rollback. Actual source defects, stock SDK fresh requests and identical SQLite/PostgreSQL scenarios checked. Original disabled inverse pending mapping, HTML, server JS and cross-pipeline/expression generation remain unverified; no new XML-RPC methods.'
    manifest['implemented_write_scope'] += ' 0.90 existing insert/update parent_key uses native schema relationships; insert collection_key calls original SObject collection methods and collection event inside the caller transaction. Recursive children, nested keywords/rename and surviving-edge deletion use shared SQLite/PostgreSQL storage with write locks and rollback. Actual source parent/ARRAY defects and stock XML-RPC calls checked. Original creator collection marker flag enabled; junction/schema definitions remain plugin/template-owned. API info, old collection commands, full collection deletion/UI lifecycle and creator template/parent/preview are not certified; no new XML-RPC signatures.'
    manifest['implemented_write_scope'] += ' 0.91 original CollectionAddCmd/CollectionRemoveCmd/CollectionDeleteCmd enabled through existing execute_cmd, with original tactic.ui.panel and collection_wdg import paths. Bulk preflight preserves circular messages without partial earlier writes; scoped markers/keys, vendor write locks and fresh identity validation prevent invalid/dangling edges. Deletion removes outgoing and incoming membership links, preserves participants, and uses native keyword/journal rollback. Actual source lifecycle/partial-success/cache defects, unchanged SDK XML-RPC, concurrent SQLite requests and real SQLite/PostgreSQL checked. HTML collection widgets and renderer actions remain outside scope; no new API methods.'
    manifest['implemented_write_scope'] += ' 0.92 original Schema.edit_connection/add_search_type(parent), SearchTypeCreatorCmd parent option and SchemaSaveCmd/SchemaConnectorCbk enabled through native scripts and existing execute_cmd paths. Registry/table creation, connector column DDL and declarative config changes share Command/Transaction/Security. Source missing-import/stale-cache/duplicate-view/id-type defects corrected; unchanged XML-RPC SDK and same SQLite/PostgreSQL contracts checked. XML graph mutation, column creation and existing-type registration remain separate original operations. HTML editor, many-to-many stub, creator templates/preview/automatic UI defaults remain excluded; no new API methods.'
    manifest['implemented_write_scope'] += ' 0.93-0.94 SearchTypeCreatorCmd template schema copy, pipeline and original definition/table/edit configs plus SideBarWdg links enabled through existing execute_cmd. Source TableUndo/pipeline/XML/append/missing-format defects corrected. Actual source runtime, unchanged SDK, SQLite/PostgreSQL and rollback checked. Separate admin-only JSON /admin/interface exposes declarative view metadata; XML-RPC and excluded HTML method formats remain unchanged. Vue reads project links and field order/titles on Refresh without rebuild; custom widgets, formatting, actions, nested navigation and UI config editing remain unported.'
    manifest['implemented_write_scope'] += ' 0.95 original headless EditWdg primitive metadata, Text/TextArea/Checkbox/Select values/options and EditCmd/EditMultipleCmd plus eight field actions restored through existing execute_cmd args/form values and native Command/SObject/Transaction/Trigger. Form context request-scoped/restored. Original runtime and unchanged SDK/Handler query_EditWdg checked on a basic named form; SQLite/PostgreSQL metadata/edit/rollback compared. Separate admin-only /admin/form descriptor. Calendar/upload/task/process/pipeline inputs, custom HTML/JS/FilterData/persistence and Vue forms remain unfinished; no full renderer/Handler parity claim.'
    manifest['implemented_write_scope'] += ' 0.96 Vue admin create/edit now consumes /admin/form primitive descriptors and saves through original execute_cmd/EditCmd. Server defaults/choices, raw sibling values, readonly exclusion, validation errors, draft cancellation and unknown write outcomes handled. Unsupported inputs/options block saving. Numeric zero conversion and Checkbox XML constructor options fixed; JSON execute_cmd exposes UserException validation messages. Browser/SQLite checked; full renderer, authoring revisions/preview and remaining specialized inputs still unfinished. The preceding 0.95 Vue limitation is superseded for this primitive subset.'
    manifest['implemented_write_scope'] += ' 0.97 modern tactic.ui.widget.CalendarInputWdg metadata/get_value and date default handlers restored, with original BaseInputWdg timezone preference and SPTDate helpers. Vue browser date/datetime-local fields retain unchanged UTC timestamps and full stored precision; changed values use server-selected timezone through original DatabaseAction/EditCmd. Day fields avoid date drift. Source day/localized-month/fallback/precision defects fixed; unknown timezone fails explicitly. JSON command results serialize date/datetime to ISO; XML-RPC unchanged. Actual original runtime, unchanged SDK/Handler procedure, SQLite/PostgreSQL and Chromium checked. Old pyasm Calendar, time-only inputs, inline calendars, HTML/JS callbacks and remaining specialized inputs are unported.'
    manifest['implemented_write_scope'] += ' 0.98 eight workflow inputs restored as headless form preparation: PipelineInputWdg, ProcessInputWdg, ReviewProcessInputWdg, SubContextInputWdg, SearchTypeInputWdg, SearchTypeWithPipelineInputWdg, ProcessGroupSelectWdg and TaskStatusSelectWdg. Whole original SubContextAction copied. Original project/global/type filtering, recursive process/context choices, group membership TSQL and status view checks retained; forms save through existing EditCmd. Original process-name bug asserted/fixed. Source runtime with intercepted HTML serialization, unchanged XML-RPC SDK and Handler task-form procedure, real SQLite/PostgreSQL and Chromium checked. No new XML-RPC signatures. Inline switching, full widget dictionaries/HTML and Handler branches directly invoking PipelineInput/empty-assignment get_display remain unfinished; group choices reflect saved state at opening, not live drafts.'
    manifest['implemented_write_scope'] += ' 0.99 TaskSObjectInputWdg, HiddenWdg and SimpleUploadWdg headless metadata restored; Vue uses existing UploadServer and execute_cmd/EditCmd/UploadAction. DateAction, TimeAction, TaskDateAction and InitialTaskCreateAction restored. Original set_sobject_value relation selection and uploaded repository mode restored. Source revision checkbox defect fixed; FileCheckin.set_revision refreshes generated auto naming. Upload ticket ownership/path confinement and journaled cleanup checked; consumed uploads survive rollback in original undo cache. Actual source runtime, unchanged XML-RPC SDK/HTTP uploader and Handler form procedure checked; SQLite/PostgreSQL and Chromium covered. Multiple/zip uploads, rich UploadWdg, immediate client actions, parent lookup popup, TimeAction browser hour/minute controls and full Handler GUI remain unfinished. No XML-RPC signature changes.'
    manifest['implemented_write_scope'] += ' 0.100 MultiUploadAction original specified/arbitrary FieldStorage workflow, custom icon precedence, context/subcontext, revision and email event restored; additive authenticated UploadServer handoff uses existing FileUpload/FileCheckin/EditCmd. Old pyasm.widget.UploadWdg and MultiSelectWdg headless metadata feed native Vue compound controls; no new XML-RPC signatures. Source runtime and its custom-icon bug, unchanged XML-RPC SDK/HTTP uploader, isolated SQLite/PostgreSQL, rollback and Chromium checked. Modern rich UploadWdg, MultiZipUploadAction, time-only controls and full HTML/GUI remain unported.'
    manifest['implemented_write_scope'] += ' 0.101 original MultiZipUploadAction restored through FileUpload/FileCheckin and safe journaled Common.unzip_file; trusted fully qualified custom naming resolver, stable object grouping, cleanup, context/subcontext and revisions. Original TimeInputWdg metadata, DateDatabaseAction and TimeDatabaseAction restored; native time control supports TimeAction hour/minute and timezone inverse. SQL time remains clock-only with unchanged seconds/microseconds retained. Actual source runtime, unchanged SDK, SQLite/PostgreSQL and Chromium checked; source cleanup/grouping/time defects asserted separately. Extraction capped at 10000 entries / 512 MiB; no prod naming, modern rich upload, time interval/HTML runtime or full GUI parity. No new XML-RPC signatures.'
    manifest['implemented_write_scope'] += ' 0.102 modern tactic.ui.widget.UploadWdg headless get_info branches restored: context_expr/context/setting precedence, original recursive pipeline choices and false pipeline flag, comment/revision/subcontext. Native Vue reuses compound upload controls and original single-file UploadAction names. Original SObject.get_icon_context restored for implicit SimpleUpload context. UploadAction now honors subcontext; source omission independently asserted, empty base context rejected before file IO. Actual source metadata/actions, unchanged SDK, SQLite/PostgreSQL and Chromium checked. No new XML-RPC signatures; immediate client actions, HTML/JS upload progress/applets and full widget dictionary/GUI parity remain excluded or unfinished.'
    manifest['implemented_write_scope'] += ' 0.103 administrator native XML authoring read/check/save uses original WidgetDbConfig.validate/SObject.commit inside Command. Raw source bytes, comments/CDATA/unknown nodes/sibling views retained; resolved WidgetConfigView layers and diff exposed separately. Database table lock plus original sobject_log revision protects parallel writers and native/XML-RPC ABA changes; repeated stale creates refused. Vue editor selects view/source, validates before save and refreshes the original renderer without rebuild. SQLite/PostgreSQL separate-process competition, original WidgetConfig contracts and Chromium checked. No XML-RPC signature changes; full revision-history browsing/AI idempotency, cross-database atomicity, filesystem source locks, renderer preview, nested layouts and AI/MCP remain unfinished.'
    manifest['implemented_write_scope'] += ' 2026-10-09 native Select builder restored from original SQL source with filters, postfix groups, joins, projections, aggregates, ordering, paging and count. Sql accepts Select/Insert/Update objects; execute and ID statements use existing read/write authorization and transaction connections. Original SQL Insert/Update execute no-op, Select copy/JSON projection loss, set_statement shadowing, group-order name, fanout join suppression and enum literal escaping defects fixed with separate source expectations. Original runtime and unchanged SDK over HTTP XML-RPC, native SQLite and real PostgreSQL private schema checked. PostgreSQL full-text predicate restored; SQLite native full-text remains explicitly unsupported. MySQL, direct Delete builder, direct Search-owned Select execution/serialization/filter/join/paging compilation and other API/core limits remain unfinished; full API parity is not claimed.'
    manifest['implemented_read_scope'] += ' 2026-10-09 original @LATEST/@CURRENT file-path expressions activated through the existing SObject-to-snapshot-to-file relationships, preserving source context/default/web handling, file ordering, single/empty results and Naming environments. Fixed source context interpolation for apostrophes. Actual original runtime (20 scenarios including two independently asserted source failures), unchanged XML-RPC SDK eval/server Python, nested read policies, parent ACL, cache invalidation/Command rollback and real isolated PostgreSQL verified. No new XML-RPC methods. Remaining expression dependencies and full API/admin parity are unfinished; original mixed-type/id-only relationship limits are not addressed by this block.'
    manifest['implemented_read_scope'] += ' 2026-10-09 original @FORMAT and StringMode format= suffix activated through existing pyasm.common.FormatValue, retaining scalar/list/empty handling, optional timecode fps, unknown-format pass-through and Naming. Missing arguments now raise SyntaxError rather than source IndexError. 77 same-body source-runtime cases cover numeric/grouped/percent/currency/date/time/scientific/boolean/dict/duration/file-size/path formats, project DATE/DATETIME settings and templates; existing Python-3/boolean/DICT fixes independently asserted. Monetary and textual-date comparisons use identical isolated locale fixtures; workers do not mutate process locale, monetary formats still require a configured monetary locale (full locale bootstrap/parity unfinished). Unchanged SDK eval/server Python/rollback and previous SDK suite, nested read policy, isolated SQLite and real PostgreSQL checked. No new XML-RPC methods; remaining expression dependencies and full API/admin parity unfinished.'
    manifest['implemented_read_scope'] += ' 2026-10-09 observed original VAR contract restored: returns an empty list (None in single mode), performs no assignment and does not evaluate argument expressions. Actual variables remain eval(vars=...) and $NAME. Incomplete arguments raise SyntaxError instead of source IndexError. 16 source-runtime scenarios cover supplied/built-in variables, opaque nested methods and Naming; 12 targeted tests include unchanged XML-RPC SDK eval/server Python and Command rollback. This does not implement a variable-assignment feature. No new XML-RPC methods; native virtual SObject/state/date contexts and full API/admin parity remain unfinished.'
    manifest['implemented_read_scope'] += ' 2026-10-09 native virtual SObject and state/date expression contexts restored using original synthesized type metadata, dynamic fields and normal/fast serialization, without creating a physical table. Virtual commit/delete and SQL generation explicitly rejected. Column permissions and nested API read policies retained. 19 actual original-runtime cases, unchanged XML-RPC SDK, server Python, state isolation, reader permissions and Command rollback verified; 17 targeted Windows tests and real isolated PostgreSQL passed. Bilingual core_model help is visible in the help catalog. S3 repository is explicitly excluded by user decision, as is Handler Repository Sync. No new XML-RPC methods; connect/site/old UI palette contexts and full API/admin parity remain unfinished.'
    manifest['implemented_read_scope'] += ' 2026-10-09 connect expression context activated through native SObjectConnection with original direction/context/result conventions. 26 original-runtime scenarios cover target filters, mixed types/projects, empty/dangling/retired results, Naming and local Search. Existing source first-type/id and SQLite EQ defects have independent expectations. Reproduced get_connected_sobjects Sudo cache leak fixed by user/Sudo-scoped keys and bypassing resolved-target cache under nested read policies. 20 targeted Windows tests and real isolated PostgreSQL passed, including unchanged SDK, server Python, reader ACL, policy restoration, writes/deletes/cache invalidation and rollback. Bilingual connections help records the homogeneous-only direct Search and original chained connection/dst_search_id projection, which does not apply ordinary destination filters. No new XML-RPC methods; site/old UI palette contexts and full API/admin parity remain unfinished.'
    manifest['implemented_read_scope'] += ' 2026-10-09 default Site provider exported through pyasm.security and original site expression branch activated. Empty installation code, original base hooks/default-project configuration, expression roots/environment/Naming retained without a database table. Missing cache identity and get_site_data classmethod defects corrected with independent source expectations. API refuses transporting provider instances as SObject records; GET fields and server-Python dictionaries remain available. Named site routing and custom providers explicitly refused before current Security/stack changes, with Command rollback after preceding writes. 37 source-runtime cases, unchanged XML-RPC SDK, nested policies, invalid-ticket boundaries, 18 targeted Windows tests and isolated PostgreSQL verified. Bilingual site_context help visible in catalog and core_model. No new XML-RPC methods; multi-site/custom-provider authentication, old UI palette and full API/admin parity remain unfinished.'
    manifest['implemented_read_scope'] += ' 2026-10-09 expression-valued add_op_filters restored via original Search.eval(single=True): two/three-part expressions and brace templates, variables, first-list/null semantics, pipe membership, groups and JSON. 30 actual source-runtime cases match. eval and query/children/snapshot/unique filter paths share scoped nested record/method policies restored after success or failure. Admin query/fast_query/children/snapshots now use existing ApiClientCmd for successful writing expressions and rollback on later filter failure; reader scripts/writes remain refused. Unchanged XML-RPC SDK, server Python, reader protected types/cross-project ACL, policy/cache boundaries and writes/rollback checked; 30 targeted Windows tests plus isolated PostgreSQL query/children/snapshots/unique lookup passed. Bilingual search_filters help visible in catalog and core_model. Dynamic timestamp filters, direct Select compilation and remaining relationship/API/admin contracts are unfinished. No new XML-RPC signatures or full parity claim.'
    manifest['implemented_read_scope'] += ' 2026-10-10 validated database-clock timestamp filters enabled through native DatabaseImpl: NOW/CURRENT_TIMESTAMP, literal-only SQLite DATETIME, PostgreSQL now()/generated intervals/precision, declared timestamp/datetime/datetime2 columns. Database evaluates the clock; SQLite normalizes dynamic RHS and stored columns to UTC without discarding column microseconds. Original quoted=True and API triple-filter rules retained, NOW special case; date-range requires parseable dates. Validator also used by automatic SQL processor values; unsafe suffix/subquery statements rejected. Nullable SQLite processor returns unquoted None; invalid numeric timestamp input raises TypeError instead of source AttributeError. 42 actual source-runtime cases on isolated fixed-clock connections include independent original bug expectations, with source PostgreSQL processor comparison distinguished from native real database execution. 31 targeted Windows tests plus isolated PostgreSQL passed: unchanged SDK/server Python, reader clock, SQL builders, offsets/precision, rejected-filter rollback and ticket lifecycle. EN/RU timestamp_filters help catalogued and cross-linked. Complex automatic SQL expressions, direct Select/Search interoperability, MySQL and full API/admin parity unfinished; no new XML-RPC method/signature.'
    manifest['implemented_read_scope'] += ' 2026-10-10 Search/owned Select share ordered WHERE/JOIN lists and native compilation; typed filters, mixed postfix groups, same-resource joins, paging, direct SQL and copies preserve bound parameters. Copies recheck current ACL. Original null/retired direct-Select bypasses corrected with independent source/native expectations. SQL rendering skips literal/comment/dollar-quoted markers; PostgreSQL bound paths escape literal percent across object/code/id/count/related reads. Cross-resource connector substitution refused; raw Sql remains authenticated-admin-only. 31 actual original-runtime scenarios, 76 related Windows tests plus Columns Editor and isolated PostgreSQL passed, including unchanged SDK and preceding-write rollback. EN/RU search_select help visible in 53-topic catalog. Owned Select dumps/loads, replacement SQL/tables/raw filter dictionaries, cross-resource direct joins, DISTINCT ON parity, MySQL and full API/admin parity remain unfinished; no new XML-RPC signature.'
    manifest['implemented_read_scope'] += ' 2026-10-10 Search-owned Select dumps/loads restored in the original JSON shape: bound WHERE values quoted on export, ordered groups/joins, aliases, aggregate/distinct/quote modes and pagination retained. Effective null/retired restrictions included; no connector/password/owner/grants serialized. Owned load requires authenticated admin/script, validates before mutation, retains receiving project/resource/connector, rechecks current ACL, reconstructs join metadata missing in source exports and clears object cache. Invalid resource/table/schema/statement/filter/projection/parameter state refused atomically; preceding writes roll back under Command. Original projected export/loader defects corrected with independent source expectations; damaged lost-name projections refused. 16 unchanged original-runtime serialization scenarios, 86 connected Windows tests and isolated PostgreSQL passed, including unchanged SDK, reader refusal, aliases/joins/literal marker text, bound filters after load and rollback. EN/RU search_select help rebuilt and checked in 53-topic runtime catalog. Replacement SQL/base tables/raw filter dictionaries, custom/cross-resource joins, DISTINCT ON parity, MySQL and full API/admin parity remain unfinished; no new XML-RPC signature.'
    manifest['implemented_read_scope'] += ' 2026-10-10 release 0.112.3 get_parent/get_all_children honor requested columns through the existing record serializer and preserve search keys/types. Source serializer projection loss has independent corrected expectations. Original runtime/SDK, server Python, retirement, project isolation, ordinary reader permissions, nested filter permissions and Command rollback verified; isolated SQLite/PostgreSQL parent-note projection matched. Core SObject.get_parent deprecated columns semantics unchanged; get_all_children instance joins and full API parity remain unfinished. Bilingual API reference and core_model Help updated.'
    manifest['implemented_read_scope'] += ' 2026-10-10 release 0.112.4 get_all_children and query(parent_key=...) use the common native instance relationship JOIN for distinct endpoint types on the same resource. Reverse single-object lookup filters the related table and the actual source key column, including unequal endpoint columns. Original missing children branch, reverse lookup and unfiltered parent query defects have independent corrected expectations. Original duplicate links, target retirement and joined-instance retirement semantics retained. 55 related Windows tests, unchanged original XML-RPC SDK, server Python, intermediate-type read permissions, projections, two projects and Command rollback passed; isolated SQLite/PostgreSQL create/read-both-directions/remove passed. Self-instance children, cross-resource instance joins, literal many_to_many relationship mode and full API parity remain unfinished. Bilingual API reference and core_model Help updated; no new XML-RPC signature.'
    manifest['implemented_read_scope'] += ' 2026-10-10 release 0.112.5 batch instance lists and relationship searches filter the actual schema source key and honor IN/NOT IN in both directions. Grouped lookup uses that key as _related_code. Source Search copies extract keys with a controlled projection, existing compiler/bound connector, filters/paging/retirement and current ACL; preloads and aliases cannot replace the key. Mixed source types/cross-resource sources refused before JOIN. Original unfiltered-list, ignored-operator/reverse-key/projection and empty-count defects have independent expectations. Duplicate links and joined-instance retirement retained; NOT IN filters joined rows, not an anti-JOIN. 20 additional original-runtime scenarios and 62 Windows tests passed, including unchanged SDK/server Python, instance read access, unequal keys and rollback; isolated SQLite/PostgreSQL batch/map/query/operator passed. Bilingual core_model and server-Python help updated. Self-instance aliases, cross-resource JOIN, aggregate source projections, fast key-helper projection and full API parity remain unfinished; no new XML-RPC signature.'
    manifest['implemented_read_scope'] += ' 2026-10-10 release 0.112.6 native get_sobject_codes/get_sobject_ids and instance-source key extraction share fast main-table value reads through the existing Search/compiler/connector. Caller projection/aliases and key-column addition retained; execution copy appends the actual base column, preserving JOIN rows, duplicates, distinct flags, explicit order/page and bound filters without implicit sorting. Original first-column defect has independent source/native expectations. Custom alter_search runs once; copied execution rechecks current main-type ACL/nested policy, including a Search created under Sudo. Retired state retained; NULL codes remain None, empty/denied main scopes return no values, cached/pending object values do not replace database keys. 22 additional actual-source scenarios and 75 Windows tests passed: unchanged SDK/server Python, projections, aliases, joins, two projects, hook/permission restoration, SQL/Select/expression paths and rollback. Isolated SQLite/PostgreSQL keys/JOIN/aliases/paging passed. Bilingual core_model/search_select and API server-Python hint updated. Grouped/aggregate key queries, self-instance aliases, cross-resource JOIN and full API parity unfinished; no new XML-RPC signature.'
    manifest['implemented_read_scope'] += ' 2026-10-10 release 0.112.7: directed same-type instance reads use explicit parent/child endpoint paths from the Handler convention, with native aliases for instance and source object tables. Shared single/list/Search filters, children, parent_key and maps replace original identity fallback defects; Results tree now uses the same kernel path. Schema code/ID endpoints, duplicates, cycles/self edges, missing/dangling links, projections/page, row-based NOT IN, alias copy/Select restore, ordinary link ACL/nested policy and Command rollback checked. 13 actual-source scenarios, 85 connected Windows regressions (two conditional PostgreSQL tests skipped), unchanged SDK/server Python, isolated SQLite/PostgreSQL and private cg.zip tree passed. EN/RU core model/Select and API Help updated. Full same-type add_instance/get_instances/remove_instance write/direction contracts still require a separate audit; cross-resource JOIN, arbitrary aggregate keys and full API parity unfinished.'
    manifest['implemented_read_scope'] += ' 2026-10-10 release 0.112.8: same-type SObject/API add_instance, get_instances and remove_instance use shared explicit child(owner)/parent(member) schema endpoints and native link Search. Original endpoint-overwrite and undirected removal defects corrected. Code/ID keys, reverse edges, duplicates, self-links, retired targets/links, stale/unsaved/missing/cross-project endpoints, invalid schema, current link read ACL, committed API operations and actual insert/delete trigger failure rollback checked. 16 actual-source cases, 91 Windows regressions (two conditional PostgreSQL tests skipped), unchanged SDK/XML-RPC, isolated SQLite/PostgreSQL and private cg.zip passed. Ordinary business writes remain administrator-only under the existing core guard; this is not complete original ordinary-user write parity. Cross-resource JOIN and full API parity remain unfinished.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.9: ordinary users can perform native project-type insert/update/delete and instance writes in authenticated Command transactions. Project/type operation ACL, actual object-project column rules, current row read policy and staged-field rechecks apply. Native bound DML reuses the account writer on SQLite/PostgreSQL with a per-statement table scope; arbitrary SQL/DDL remains blocked. Automatic journals, own-redo cleanup and integral global-search indexing are retained; index writes use bounded native Sudo and restore authority. 17 actual-source cases distinguish original permissive view/edit insertion and missing project-write checks from corrected native denials. 111 Windows checks passed (113 total, two conditional PostgreSQL skipped); separate real PostgreSQL/SQLite, unchanged SDK/XML-RPC, fields/types/project denials, trigger/bulk rollback, existing accounts/messages and private cg.zip checked. System/definition writes, file operations, status/workflow side effects, ordinary persistent diagnostics and full API parity remain open.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.10: authenticated ordinary-user DebugLog/ExceptionLog and existing API log use an independent owned Command with an exact diagnostic SObject write scope. Author identity, system resource, insert/generated-code update and final bound data are checked; raw DML/DDL and direct log table writes/deletion remain guarded. Logging does not share or roll back an active system writer, which still fails explicitly. Root command failure clears all nested stack entries so the next command rolls back normally. Batch replaces its bootstrap admin context and closes connections after ordinary login. Actual source ordinary/admin diagnostic calls, unchanged SDK/XML-RPC, API method denial, nested/next-command rollback, identity and SQLite/PostgreSQL checked. StatusLog/Workflow user side effects, file permissions and full API parity remain unfinished.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.11: ordinary-user task insert/edit/delete and API create_task use the existing native Command/SObject path. Task logical project, type operation, current row, staged/final column rules and visible editable project parent are checked. Parent code/id must agree; ownership changes remain explicitly unsupported for ordinary users. StatusLog.create rechecks its source and temporarily authorizes only the exact history SObject and generated-code assignment, without Sudo or general system SQL. History shares the caller transaction, authenticated author and actual source project; cross-project history corrects the source current-project bug. Actual source runtime, unchanged SDK/XML-RPC, completion trigger, no-op, bulk/trigger/history failure rollback, revoked fields, raw SQL/forged history denial and SQLite/PostgreSQL checked. Workflow process_state remains administrator-only; its ordinary-user dependency failure rolls back preceding task/history changes. Other Workflow effects, files and full API parity remain unfinished.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.12: declarative Workflow transitions and existing call_pipeline_event allow authenticated ordinary users with a visible editable project-object parent. Native graph validation/locking and task ACLs remain. Exact effect SObjects temporarily authorize process_state, messages/history and native revise-error notes in the caller transaction. Parent identities, logical project/resource, author, immutable ownership, current read policy and staged/final columns are checked; raw SQL, direct effects, definitions, custom handlers and Python callbacks remain restricted. States and messages use their actual parent project even when the current request differs. Scope restoration and generated codes are retained without Sudo. Actual source ordinary-user states/status/messages matched, preserving the earlier pipeline owner correction; unchanged SDK/XML-RPC, SQLite/PostgreSQL and late failure/field/parent denial rollback verified. Script ACLs, complete cross-project graph coverage, file permissions and full API parity remain open.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.13: ordinary trusted PythonCmd/PythonTrigger and execute_python_script reuse the source api_cmd key tactic.command.PythonCmd. An explicit allow plus current project allow is required regardless of api_cmd_restricted; default ordinary execution stays denied. Authenticated identity, active persisted account, active Command and persisted administrator checks reject Sudo/forged admin. The Python-only checker branch does not open other administrative callers, SQL, config writes, custom node handlers or expression Python. Native Mako, script input, saved/inline code and same-caller SDK/transaction remain. Actual original ordinary inline/saved Workflow callbacks and parent updates match; unchanged SDK/XML-RPC, PythonTrigger, project/field/api_method denial, callback/write rollback and SQLite/PostgreSQL checked. Scripts are trusted server Python, not a sandbox or per-path ACL. Full cross-project Workflow and file/API parity remain open.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.14: cross-project Workflow process definitions are read from the pipeline owner; handlers reuse the generation-aware Pipeline cache. Native process events temporarily select the actual parent project before trigger selection/execution, preserving authenticated identity, connection pool and Command transaction, then restore context in finally. Project-scoped PythonCmd grants and saved script paths follow the callback project. Dependency start, waiting child task, return completion, inline/saved callbacks, project/type/grant denials and late rollback across two physical project databases pass on SQLite/PostgreSQL and unchanged SDK/XML-RPC. Four unchanged source process lookups isolate the original caller-database bug. Native project config creation/import and owned Store.upgrade migrate process_state.state to PostgreSQL text, preserving old JSON and permitting long waiter data. Source per-database commits remain, with no distributed atomic commit guarantee. Cross-project hierarchy/progress/overrides and full file/API parity remain unverified.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.15: ordinary active users may upload to their ticket directory and run native simple_checkin against an editable visible project object. Project, parent type, snapshot/file operation and column rules are checked; repository metadata keeps its own parent, project and existing snapshot ownership. Bound SQL matches staged values including PostgreSQL JSON. FileUndo is authorized only within the upload/native check-in scope; raw SQL, arbitrary FileUndo and other file write API methods remain closed. API inplace/local/custom-class requests remain admin-only. Native trusted Python FileCheckin keeps its source modes and scoped authorization. Rollback restores only nodes emitted by validated FileUndo when their scope has ended. Version allocation, flags, versionless copies and image main/web/icon are native; late failure preserves old files/rows and consumes create uploads into the original undo cache. SQLite/PostgreSQL and unchanged SDK/XML-RPC exercise versions, previews, denials and rollback. Full file/check-out/undo/HTTP/append/group permissions and full API parity are not verified.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.16: ordinary active users may also call add_file, group_checkin and add_group through the same native Checkin/FileUndo transaction scope. Append resolves the existing visible snapshot parent; project, parent, snapshot/file and column rules remain mandatory. Group File/FileGroup drafts receive search_code before their first commit; factories retain their original signatures and default behavior. Ticket upload/handoff paths, strict naming with explicit latest-versionless definitions, array append, group ranges/steps/metadata, missing frames, path containment, ACL denials and late rollback of rows and existing files/aliases verified on SQLite/PostgreSQL. Unchanged XML-RPC SDK add_file/add_group use already uploaded files with mode=None; SDK group_checkin manual mode reads its own ticket handoff directory. HTTP upload, check-out and ordinary-user journal undo/redo remain unverified; full API parity is false.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.17: HTTP UploadServer admits active authenticated users to private ticket staging without an admin/project grant, matching original UploadServerWdg. The HTTP-only ticket_upload scope still validates persisted active identity, configured API method rules and Command transaction; it grants no object/repository write permission. XML-RPC binary upload retains its project allow check and native check-in retains parent/type/snapshot/file/column ACLs. HTTP create/append, binary Unicode chunk/resume, empty files, cross-ticket/custom-dir/path guards, retired identity and late multi-file rollback verified on private SQLite/PostgreSQL fixtures. Unchanged SDK automatic HTTP upload followed by simple_checkin/group_checkin/add_file/add_group verified against a temporary XML-RPC/HTTP server. Upload chunks are separate committed requests; offset resumes are client-controlled and ambiguous append retry is not idempotent. Ordinary-user check-out and journal undo/redo remain unverified; full API parity is false.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.18: ordinary-user checkout uses the original Snapshot path selection, version/level/lock policy and both checkout callbacks inside native Command. It requires current parent-project allow and view access to parent/snapshot/selected File/level types, records and columns; missing or hidden File references are rejected before callbacks. The callback caller is the executing Command, fixing ApiXMLRPC.errors masking the original callback failure. No sudo or Checkin:writing scope is added; callback writes retain actual-user ACL and Python callbacks retain explicit PythonCmd permission. SQLite/PostgreSQL and unchanged XML-RPC SDK copy/download/sandbox, current/versionless/explicit versions, all file types and level selection verified. Same-transaction late callback rollback preserves rows/journals/files. Cross-project checkout for ordinary users remains denied; client IO occurs after RPC and is not covered by server rollback. Static repository HTTP aliases retain original public semantics. Grouped frame expansion, level-scoped aliases and ordinary-user journal undo/redo remain unverified or guarded; full API parity remains false.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.19: ordinary-user undo/redo exposes the native UndoCmd/RedoCmd and SObjectUndo for persisted own project CRUD journals. Replay locks the journal row on PostgreSQL or starts SQLite IMMEDIATE, rereads the canonical record, checks unchanged payload, authenticated owner, current namespace and undo/redo direction, then preflights project, inverse-operation type/record/column grants and node project/site boundaries. Actual SObject writes retain native permissions; missing/filtered ordinary-user update/delete targets fail rather than silently completing the journal. Integral sthpw/sobject_list nodes must refer to a project object in that same journal by code or original ID; only these index nodes use native scoped Sudo. No whole-journal sudo or general file/schema/system write scope is opened. SQLite/PostgreSQL and unchanged SDK XML-RPC verify insert/update/rename/delete, default/explicit selection, redo branch invalidation, late undo/redo rollback including index/journals, foreign owner/project, stale direction, column/object/type/project/method denials, staged-payload tampering and concurrent duplicate undo. Original admin object/file/schema/client-session contracts remain valid. Ordinary-user file/upload/check-in/schema/task/note/system/multisite journals, arbitrary execute_transaction and resumed client transactions remain guarded. ignore_files does not bypass the ordinary-user boundary. Native replay timestamp/ID and separate-database commit boundaries remain; full API parity is false.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.20: ordinary-user persisted own check-in journals replay native SObjectUndo/FileUndo/FileUndoReplay, with the existing canonical owner/project/direction lock. Preflight validates original visible editable project parents, repository view/inverse-operation record/column ACL, immutable metadata anchors, complete file journals and recorded paths against parent file metadata, original private ticket uploads and durable undo caches. FileGroup/FileRange expands frame sequences. A per-node Checkin:writing scope authorizes only its own snapshot/file record or file node; no administrator elevation is used. Complete journals restore versionless metadata and IO themselves instead of regenerating aliases during is_latest/is_current replay. Native numeric identity fields from XML compare consistently with stored typed IDs. File replay compensation owns its exact attempted nodes after request scope cleanup; pending create redo removes partial output only when the complete cache remains. SQLite/PostgreSQL and the unchanged SDK verify first/second version, versionless, append, frame groups, permission/path denials, late metadata/IO failures and partial disk writes. Isolated upload journals, metadata-only ignore_files replay, schema/task/note/other-system/multisite and resumed sessions remain guarded. Native regenerated row IDs, timestamps and independent-database partial-commit boundaries remain; full API parity is false. Repository Sync/S3 are excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.21: ordinary-user create_note uses the existing native factory and Command with authenticated-author, current-project parent/type/record/column ACL. Own task/note journals replay through native SObjectUndo with canonical owner/project/direction locking, fresh visible original editable project parents and immutable ownership metadata. Notes require the current author; privileged private-note reads do not grant foreign writes. Bound note SQL must match its staged record. Reply creation validates the visible same-parent thread; deleting a parent with replies is refused, with scoped integrity-only sudo to detect private children. Note insert/delete replay preserves numeric IDs to retain parent_id links; historical insert journals capture the original ID before undo and persist that anchor. ID collisions fail and roll back instead of overwriting another note. The unchanged shared original/native thread probe documents the deliberate source bug fix: original restoration loses thread identity, native retains it. SQLite/PostgreSQL and unchanged SDK verify task/note CRUD, note rename, threads, author/ACL denials, historical IDs, collisions and late batch rollback. Task status journals with status_log/Workflow/process_state/message or other unsupported system effects remain guarded as a whole; effects are never skipped. Reparenting, system-object note parents, schema/standalone-upload/multisite/resumed-session replay remain guarded. Independent-database partial commit remains; full API parity is false. Repository Sync/S3 are excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.22: own single-project task-status/Workflow journals replay native SObjectUndo together with status_log, process_state, messages/history and own notes. Workflow messages, previously excluded by source SObjectUndo, now enter the same native journal only under their exact Workflow:writing scope; the complete-backup XML marker distinguishes new Workflow journals. Historical state/message journals without this marker are refused instead of partially replayed. Canonical owner/project/direction, original visible editable parents and status sources, immutable ownership, history author and current inverse-operation/view/record/column ACL are checked before writes. Derived effect permissions follow their authorized parent unless explicitly denied, as forward Workflow effects do. Per-node Workflow:replay scopes permit only that exact record/operation/staged bound SQL and restore in finally; no journal-wide sudo. Task/process_state IDs are preserved, like note IDs, to retain status_log source links; collisions fail. GMT timestamp redo uses the stored database clock, correcting native local-time reconversion. PostgreSQL bound SQL reuses native dialect conversion for JSON/scalar values. SQLite/PostgreSQL and unchanged SDK verify pending/progress/completion, messages/packages, history, permission/read-filter/forged-SQL/other-record denials and late rollback. An unchanged source/native probe records source partial Workflow restoration with stale status/messages, native complete restoration and equal GMT date preservation. Cross-project/unsupported-system/history-without-backup/schema/standalone-upload/multisite/resumed-session replay remains guarded. Legacy unscoped pipeline adoption replay is not opened; independent-database partial commit remains. Full API parity is false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.23: ordinary own saved Workflow journals replay across physical project databases through native SObjectUndo. The canonical journal lock retains its authenticated owner, initiating namespace and direction. Derived effects and their original parent/status source require actual-project read/write/view/inverse/record/column rights; explicit project access is required. Cross-project business/task/own-note/index nodes are allowed only for the original visible editable parents proven by the validated Workflow effects in that same journal; unrelated foreign-project CRUD remains refused. The existing exact per-node scope and staged bound SQL guard remain, without journal-wide sudo or callback reexecution. SQLite/PostgreSQL and unchanged XML-RPC SDK test dependency start/return/completion, callbacks results and own notes, task/note/state IDs, denials in both projects, wrong journal namespace and late rollback after writing both project DBs including system history/index/journal. An unchanged source/native probe explicitly checks original caller-database routing and stale messages versus native actual-project states and complete message restoration. Historical Workflow without complete backups, legacy empty-pipeline adoption, unrelated cross-project CRUD/file IO, unsupported system/schema/standalone-upload/multisite/resumed-session replay remain guarded. External effects are not undone; sequential independent DB partial commit remains, not distributed atomicity. Full API parity is false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.24: own complete Workflow journals replay native adoption of an existing legacy process_state whose pipeline_code was empty. Only a recorded update from empty to the original visible parent primary pipeline is allowed; its visible process definition (or __PIPELINE__ aggregate) is required. Every recorded pipeline transition must form that same owner chain, all nodes for the adopted state must update the existing row, the original state ID is checked, and the current owner must match the journal direction. Each node receives its recorded before/after owner for the existing exact runtime scope; other ownership remains immutable. No direct user process_state write, blanket sudo or arbitrary pipeline switch is opened. SQLite/PostgreSQL and unchanged XML-RPC SDK check cross-project dependency start/completion, own notes, original IDs, state preservation, current/parent/journal owner tampering, actual pipeline-column/process-view denials, forged bound SQL and late rollback of both project databases/system journal. An unchanged source/native probe records original unowned state and stale messages versus native owner adoption, undo to empty and complete message replay. Historical missing message backups, unrelated cross-project CRUD/file IO, unsupported system/schema/standalone-upload/multisite/resumed-session replay remain guarded. Already sent effects cannot be undone; independent database partial commit remains, without distributed atomicity. Full API parity is false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.25: ordinary-user checkout accepts a parent search key from another project. Parent-project access is checked before rebinding only the project field of the existing request context; identity, security, container, Command, transaction and SQL pool remain unchanged. Snapshot selection, naming/sandbox and config callbacks run in the actual parent project; context is restored in finally on success or failure. Every referenced project and loaded parent/snapshot/selected File/level record and column requires view access, including a level in a third project. PythonCmd callback grants are checked in the actual parent project; caller-project triggers/grants do not substitute for them. No sudo or repository-write grant. SQLite/PostgreSQL and unchanged XML-RPC SDK verify versions/current/versionless/all types, levels, copy/download/sandbox, denied access, locks/hidden references, saved Python/class callbacks and late rollback/context restoration. An unchanged source/native probe records the original missing checkout callback versus native actual-parent callback with caller context restored. Grouped frame expansion, level-scoped aliases and unrelated cross-project callback journal replay remain unverified. Client IO after RPC is outside server rollback; static repository URLs retain their public Apache semantics. Independent database partial commit remains. Full API parity is false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.26: checkout expands selected sequence File references with native FileRange/FileGroup into matching ordered client_lib_paths, sandbox_paths and web_paths before callbacks. Ordinary files and directories retain their existing paths; a specific file_type still selects the first matching XML node, while * retains XML file order. File metadata supplies the sequence range; mismatched path/reference counts and corrupt ranges fail before callbacks. No new signature, identity/write grant or client bridge. The unchanged original SDK now copies/downloads/checks out sequences to sandbox using concrete frame paths. SQLite/PostgreSQL and SDK check hash and printf inputs, stepped/negative frames, versions/current/latest, multiple sequence types mixed with an ordinary file, actual bytes, project/record/column rights, corrupt ranges, actual-parent callbacks, context restoration and late rollback. An unchanged source/native probe records the original single pattern versus three matching native frame paths; missing original checkout callbacks remain an explicit correction. 32 targeted Windows regression tests and isolated PostgreSQL pass. Bilingual existing Check-in/Core model/API Help updated. Level-scoped aliases and unrelated cross-project callback replay remain unverified. Server checkout performs no client IO; later client failure may leave partial local copies and cannot undo a successful RPC. Static repository aliases remain public; independent database partial commit remains. Full API parity false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.27: Snapshot versionless lookup/create/update uses exact level_type/level_id, including the unscoped case. Public source signatures remain unchanged; private _get_versionless carries the level scope for native update_versionless and API get_snapshot/get_paths. Each level keeps separate latest/current rows and File ownership; current remains unchanged when a newer check-in has is_current=False. Existing physical destinations outside the selected alias are rejected before FileUndo replacement, so bad naming cannot overwrite another level. Native Command/FileUndo, identity, parent/snapshot/file/column write ACLs and rollback remain active. Private SQLite/PostgreSQL and unchanged SDK verify three scopes, versions, stable alias codes, bytes, ACL denials, late trigger rollback and colliding naming. The unchanged original/native probe records the source returning the same final versioned snapshot for every requested level, while native returns six correct level aliases. Source comparison uses a normal business project: system projects intentionally ignore database naming. Existing EN/RU Check-in/Core model/API Help updated. Level alias delete/promotion and level-specific durable replay are not verified here; delete remains guarded. Cross-project alias authoring and MySQL are not covered by these tests. Existing static repository public URLs and independent database partial commit boundaries remain. Full API parity false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' 2026-10-10 release 0.112.28: Administration shell and all eight sections compared with current Handler Qt/QML on isolated fixtures at 1400x940 and 900x620, including nested pages. Independent section drafts, close/project guards, 250/56px navigation, scoped form IDs, native catalog/tab/splitter layouts and keyboard/port graph interaction verified in Chromium. Native Progress defaults now pass the resolved current process to the original trigger record instead of None; listener creation checked through authenticated WorkflowCmd. Existing native command validation, revision conflicts, ACLs, unknown XML retention and rollback preserved. Administration native regressions use isolated SQLite; this release does not establish MySQL/PostgreSQL acceptance, complete pixel parity or configured custom-class/runtime parity. Configuration and working panels remain separate blocks. Full API parity false; Repository Sync/S3 excluded.'
    manifest['implemented_write_scope'] += ' Forced explicit-ID inserts retain native plugin/template identity and insert ACLs; fresh row visibility checks apply to actual edits/deletes, not nonexistent new rows. Enabled Workflow status-trigger script preflight remains admin-only, verified to roll back task/history. Ordinary-user Workflow task transitions are not completed.'
    manifest['implemented_write_scope'] += ' 0.112.33: browser Drop Plate and Commit Queue use extracted Handler file matching and extended naming/check-in through the exact BrowserCheckinCmd. Match/templates/plan are read-only; ordinary-user checkin preserves owner/project/snapshot/file/column ACLs, native locks, IconCreator and Command/FileUndo. Metadata group inplace replacement and deletion preserve every member with rollback/undo/redo, including unchanged Handler scripts. Repository-root HTTP presentation is corrected. Private SQLite and Chromium scenarios verified; production PostgreSQL/MySQL and physical phones unchecked. Full API parity remains false; Repository Sync, S3 and desktop/DCC connections excluded.'
    manifest['implemented_write_scope'] += ' 0.112.37: ordinary-account get_unique/clone/retire/reactivate and snapshot create/lock/unlock/current use native object/field/project ACLs; internal RetireLog author/code writes remain scoped. Remote XML-RPC and local SDK share parent-bound check-in authorization with nested-scope restoration; late Python failure rolls back objects, logs and snapshots. Native diagnostic missing_method returns False; unknown RPC still faults. Current Handler static inventory refreshed; original batch naming, note history and chat/check-in scripts tested. 122 entry points of 129 exposed signatures are available; five HTML/PyV8 contracts remain pending, two deprecated-production methods excluded. Full behavior parity remains false.'
    manifest['implemented_write_scope'] += ' 0.112.39: five HTML/server-JS entry contracts connected, bringing availability to 127/129 (two production exclusions). Native Widget/HTML/Palette/buffers, migrated TableLayout cells, top_layout state, JsCmd/custom_script and original JS SDK restored. QuickJS-NG replaces PyV8 with a synchronous JSON/API bridge, persisted administrator checks and Command rollback. Widget keys bind login/ticket and optional builtin/input restrictions; HTML classes must derive from Widget. Unported classes/full application/full interactive table HTML/Help/grouping/hierarchy fail explicitly. Source single-key and first id=-1 behavior retained; nested options, writer creation, request buffers/WebState and constructor options corrected. Server JS is visible in shared Script Editor/Shelf and PythonTrigger. Actual original-runtime basic HTML/palette comparison, private XML-RPC/SDK/Chromium and installed-wheel checks; asynchronous JS, arbitrary PyV8 Python-object interop and original PyV8 runtime not verified. Full behavior parity false; Repository Sync/S3/DCC excluded.'
    manifest['implemented_write_scope'] += ' 0.112.40: dictionary API info and affected SObjects reach ApiClientCmd listeners; command keys bind login/ticket and static kwargs with resolved-class policy and can_run retained. use_transaction=False skips nested hooks, while outer API rollback remains native. Delete SQL builder restored with trailing-AND/quote/NULL fixes and empty-filter refusal; raw SQL remains admin/Command/resource scoped. Snapshot deletion now handles level-specific latest/current aliases without deleting other levels/default aliases, with file/row rollback. Named view_as_attr XML works without @ across save/reload/reorder. Source comparisons and private failure/security tests retained. Full old HTML shell further migration excluded by user on 2026-10-11; working HTML methods preserved. MySQL deferred; remaining SQL/domain/remote variants documented rather than claimed complete.'
    manifest['implemented_read_scope'] += ' 0.112.40: native COLOR/GRADIENT/PALETTE expressions enabled, headless gradient adapter supplied; source palette fallbacks retained. Gradient offsets use data literals rather than arbitrary Python. Bilingual Help contains variant matrix and static UnsupportedContract inventory instructions; these are not exhaustive runtime parity.'
    return manifest


class ApiXMLRPC:
    _signatures = {}

    def __init__(self, store):
        self.store = store
        self.auth = Authenticator(store)
        self.protocol = 'xmlrpc' 

    def _get_data(self):
        # Original BaseApiXMLRPC state belongs to the current request Container.
        key = 'ApiXMLRPC:%s' % hash(self)
        data = Container.get(key)
        if data is None:
            data = {'info': {}, 'sobjects': []}
            Container.put(key, data)
        return data

    def set_sobjects(self, sobjects):
        self._get_data()['sobjects'] = sobjects

    def set_sobject(self, sobject):
        self.set_sobjects([sobject])

    def get_sobjects(self):
        return self._get_data()['sobjects']

    def update_info(self, info):
        self.get_info().update(info)

    def get_info(self):
        return self._get_data()['info']

    def get_release_version(self, ticket):
        '''DEPRECATED: use get_server_version()'''
        return Environment.get_release_version()

    def get_server_version(self, ticket):
        '''get the server version'''
        return Environment.get_release_version()

    def get_server_api_version(self, ticket):
        '''get the server version'''
        return Environment.get_release_api_version()

    def add_instance(self, ticket, search_key1, search_key2):
        '''Add an instance between two sobjects.  This requires that there
        is a instance relationship between the two sobjects defined in the
        schema

        @param:
        search_key1: the search_key to the first sobject
        search_key2: the search_key to the first sobject

        @return:
        the instance sobject created
        '''

        sobjects = [self._sobject(search_key1)]
        if sobjects:
            sobject1 = sobjects[0]
        else:
            raise LookupError("SObject [%s] does not exist" % search_key1)

        sobjects = [self._sobject(search_key2)]
        if sobjects:
            sobject2 = sobjects[0]
        else:
            raise LookupError("SObject [%s] does not exist" % search_key2)

        instance = sobject1.add_instance(sobject2)
        sobject_dict = self._record(instance)
        return sobject_dict

    def get_instances(self, ticket, search_key, search_type):
        '''Get all the instances of an sobject of a certain stype.  There
        must be an instance relationship between the sobject and the search
        type

        @param:
        search_key: the search_key to the sobject to get the instances
        search_type: the search_type of the related sobjects that the instances
            are attached to

        @return:
        the instance sobject created
        '''
        sobjects = [self._sobject(search_key)]
        if sobjects:
            sobject = sobjects[0]
        else:
            raise LookupError("SObject [%s] does not exist" % search_key)

        instances = sobject.get_instances(search_type)

        instance_dicts = []
        for instance in instances:
            instance_dict = self._record(instance)

            instance_dicts.append(instance_dict)
        return instance_dicts

    def remove_instance(self, ticket, search_key1, search_key2):
        '''Removes the instances between these two sobjects

        @param:
        search_key1: the search_key to the first sobject
        search_key2: the search_key to the first sobject

        @return:
        the instance sobject created
        '''

        sobjects = [self._sobject(search_key1)]
        if sobjects:
            sobject1 = sobjects[0]
        else:
            raise LookupError("SObject [%s] does not exist" % search_key1)

        sobjects = [self._sobject(search_key2)]
        if sobjects:
            sobject2 = sobjects[0]
        else:
            raise LookupError("SObject [%s] does not exist" % search_key2)


        sobject1.remove_instance(sobject2)

    def create_search_type(self, ticket, search_type, title, description='', has_pipeline=False):
        '''Method to create a new search type

        @params:
        search_type - Newly defined search_type
        title - readable title to display this search type as
        description - a brief description of this search type
        has_pipeline - determines whether this search type goes through a
            pipeline.  Simply puts a pipeline_code column in the table.

        @return
        the newly created search type

        '''
        from tactic.core.schema_commands import SearchTypeCreatorCmd

        project_code = Project.get_project_code()
        kwargs = {
            'database': project_code,
            'namespace': project_code,
            'schema': 'public',

            'search_type_name': search_type,
            'asset_description': description,
            'asset_title': title,
            'sobject_pipeline': has_pipeline,
        }

        creator = SearchTypeCreatorCmd(**kwargs)
        creator.execute()

        sobject = creator.get_search_type_obj()
        sobject_dict = self._record(sobject)
        return sobject_dict

    def add_column_to_search_type(self, ticket, search_type, column_name, column_type):
        '''Adds a new column to the search type

        @params
        ticket - authentication ticket
        search_type - the search type that the new column will be added to
        column_name - the name of the column to add to the database
        column_type - the type of the column to add to the database

        @return
        True if column was created, False if column exists
        '''

        from pyasm.search import DbContainer
        search_type_sobj = SearchType.get(search_type)
        table = search_type_sobj.get_table()

        db_resource = Project.get_db_resource_by_search_type(search_type)
        database = search_type_sobj.get_database()

        sql = DbContainer.get(db_resource)

        # Check to see if column exists
        table_info = sql.get_column_info(table)
        if table_info.get(column_name):
            return False

        sql.add_column(table, column_name, column_type)
        # The source API omitted the journal recorded by its AddColumnCmd.
        from pyasm.search import AlterTableUndo
        AlterTableUndo.log_add(db_resource, table, column_name, column_type)

        return True

    def connect_sobjects(self, ticket, src_sobject, dst_sobject, context='default'):
        '''connect two sobjects together

        @params
        src_sobject: the original sobject from which the connection starts
        dst_sobject: the sobject to which the connection connects to
        context: an arbirarty parameter which defines type of connection

        @return
        the connection sobject
        '''
        from pyasm.biz import SObjectConnection

        if isinstance(src_sobject, dict):
            src_sobject = src_sobject.get('__search_key__')
        if isinstance(dst_sobject, dict):
            dst_sobject = dst_sobject.get('__search_key__')

        sobject_a = self._sobject(src_sobject)
        sobject_b = self._sobject(dst_sobject)
        if not sobject_a:
            raise LookupError('Source sObject [%s] is not found ' %src_sobject)
        if not sobject_b:
            raise LookupError('Destination sObject [%s] is not found ' %dst_sobject)
        connection = SObjectConnection.create(sobject_a, sobject_b, context)
        sobject_dict = self._record(connection)
        return sobject_dict

    def get_connected_sobjects(self, ticket, src_sobject, context=''):
        '''get all of the connected sobjects

        @params
        src_sobject: the original sobject from which the connection starts
        context: an arbirarty parameter which defines type of connection

        @return
        a list of connected sobjects
        '''
        from pyasm.biz import SObjectConnection
        if isinstance(src_sobject, dict):
            src_sobject = src_sobject.get('__search_key__')

        sobject_a = self._sobject(src_sobject)

        if not sobject_a:
            raise LookupError('Source sObject [%s] is not found ' %src_sobject)

        connections, sobjects = SObjectConnection.get_connected_sobjects(sobject_a, context=context)
        sobject_list = []
        for sobject in sobjects:
            sobject_dict = self._record(sobject)
            sobject_list.append(sobject_dict)
        return sobject_list

    def get_connected_sobject(self, ticket, src_sobject, context=''):
        '''get all of the connected sobjects

        @params:
        src_sobject - the original sobject from which the connection starts
        context - an arbirarty parameter which defines type of connection

        @return:
        a single sobject
        '''
        from pyasm.biz import SObjectConnection
        if isinstance(src_sobject, dict):
            src_sobject = src_sobject.get('__search_key__')

        sobject_a = self._sobject(src_sobject)
        if not sobject_a:
            raise LookupError('Source sObject [%s] is not found ' %src_sobject)

        sobject = SObjectConnection.get_connected_sobject(sobject_a, context=context)
        sobject_dict = self._record(sobject)

        return sobject_dict

    def class_exists(self, ticket, class_path):
        '''determines if a class exists on the server

        @params
        ticket - authentication ticket
        class_path - fully qualified python class path

        @return
        boolean: true if class exists and can be seen
        '''

        from importlib import import_module
        if not isinstance(class_path, str) or not all(part.isidentifier() for part in class_path.split('.')):
            return False
        module_path, _, class_name = class_path.rpartition('.')
        if not module_path:
            return False
        try:
            return hasattr(import_module(module_path), class_name)
        except Exception:
            return False

    def check_access(self, ticket, access_group, key, access, value=None, is_match=False, default="edit"):
        '''check the access for a specified access_group name like search_type, sobject, project,
            or custom-defined '''
        security = Environment.get_security()
        return security.check_access(access_group, key, access, value, is_match, default = default)

    def upload_file(self, ticket, filename, data):
        from xmlrpc.client import Binary
        from pyasm.search import FileUndo
        filename = upload_file_name(filename)
        payload = data.data if isinstance(data, Binary) else data
        if not isinstance(payload, (bytes, bytearray)):
            raise ValueError('Upload requires binary data')
        FileUndo._check_access()
        upload_path = os.path.join(Environment.get_upload_dir(), filename)
        staged = None
        try:
            with tempfile.NamedTemporaryFile(dir=Environment.get_tmp_dir(), delete=False) as file:
                staged = file.name
                file.write(payload)
            FileUndo.create(staged, upload_path)
        finally:
            if staged and os.path.exists(staged):
                os.unlink(staged)
        return True

    def get_upload_file_size(self, ticket, filename):
        filename = upload_file_name(filename)
        upload_path = os.path.join(Environment.get_upload_dir(), filename)
        return os.path.getsize(upload_path) if os.path.isfile(upload_path) else 0

    def http_upload(self, fields, uploads):
        """UploadServer's ticket directory and create/append actions, without the old UI renderer."""
        from io import BytesIO
        from pathlib import Path
        from types import SimpleNamespace
        from pyasm.command import Command, FileUpload
        from pyasm.search import FileUndo
        token = fields.get('login_ticket') or fields.get('ticket')
        login, state_xml = self.auth.validate(token, return_state=True)
        from pyasm.common import Xml
        state_data = Xml(state_xml) if state_xml else None
        if state_data and state_data.get_root_node().tag != 'state':
            raise ValueError('Expected state XML root')
        transaction_id = state_data.get_value('state/transaction') if state_data else None
        project = state_data.get_value('state/project') if state_data else 'admin'
        if any(fields.get(name) not in (None, '', token) for name in ('ticket', 'transaction_ticket')):
            raise UnsupportedContract('Uploads to another transaction ticket are not migrated')
        if fields.get('upload_dir'):
            raise UnsupportedContract('Custom HTTP upload directories are not migrated')
        action = fields.get('action') or 'create'
        if action not in ('create', 'append'):
            raise ValueError('Invalid upload action')
        subdir = fields.get('subdir', '').replace('\\', '/')
        from pyasm.checkin.repo import _check_file_name
        if subdir:
            for component in subdir.split('/'):
                _check_file_name(component)
        if not uploads:
            raise ValueError('An uploaded file is required')
        with request_context(RequestContext(self.store, login, project or 'admin')):
            self.auth.bind_security(login, token)
            self.check_method_access('upload_file')
            # UploadServer stages private ticket files before a project/object is selected.
            Container.put('Checkin:writing', {'parent': None, 'ticket_upload': True})
            command = Command()
            command.get_transaction().set_sync(False)
            def execute():
                if state_xml:
                    from pyasm.search import DbContainer, TransactionState, TransactionLog
                    transaction = command.get_transaction()
                    sql = DbContainer.get(self.store.get_db_resource())
                    transaction.register_database(sql)
                    sql.lock_transaction_state(token)
                    state = TransactionState.get_by_ticket(token)
                    log_id = state.get_state('transaction') if state else None
                    if transaction_id and str(log_id) != str(transaction_id):
                        raise ValueError('Client transaction was closed before this upload')
                    if log_id:
                        log = TransactionLog.get_by_id(int(log_id))
                        if not log or log.get_value('login') != login or log.get_value('type') != 'undo':
                            raise SecurityException('Transaction does not belong to the current user or is closed')
                        transaction.set_transaction(log)
                        transaction.set_title(log.get_value('title'))
                        transaction.set_description(log.get_value('description'))
                root = Path(Environment.get_upload_dir())
                directory = root / subdir
                if not directory.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Upload directory must stay inside the ticket directory')
                paths = []
                for name, payload in uploads:
                    target = directory / upload_file_name(name)
                    if not target.resolve().is_relative_to(root.resolve()):
                        raise ValueError('Upload file must stay inside the ticket directory')
                    FileUndo.mkdir(str(directory))
                    upload = FileUpload()
                    upload.set_create_icon(False)
                    upload.set_append_mode(action == 'append')
                    upload.set_file_dir(str(directory))
                    upload.set_field_storage(SimpleNamespace(filename=name, file=BytesIO(payload)), name)
                    upload.execute()
                    paths.extend(upload.get_files())
                return paths
            command.execute = execute
            return Command.execute_cmd(command)

    def dispatch(self, method, args, kwargs=None, environ=None):
        started = time.perf_counter()
        log_enabled = LOG.isEnabledFor(logging.INFO)
        timestamp = datetime.now() if log_enabled else None
        record = dict(user='anonymous', project='', ticket='', arguments=[], method=method,
                      log_enabled=log_enabled, environ=environ or {})
        status = 'OK'
        request_id = '%s - #%07d' % (threading.get_ident(), next(REQUEST_COUNT))
        try:
            return self._dispatch(method, args, kwargs, record)
        except Exception as error:
            status = type(error).__name__
            raise
        finally:
            if log_enabled:
                from pyasm.web.api_xmlrpc import print_primary_info, print_secondary_info
                global LAST_RSS
                with LOG_LOCK, StringIO() as output:
                    print_primary_info(request_id, timestamp, record['user'], record['method'],
                                       record['ticket'], record['arguments'], output)
                    if status != 'OK':
                        print('error: %s' % status, file=output)
                    duration = time.perf_counter() - record.get('method_started', started)
                    rss = System().memory_usage().get('rss')
                    increment = rss - LAST_RSS
                    LAST_RSS = rss
                    print_secondary_info(duration, request_id, rss, increment, output)
                    print('Total Duration: %0.3f seconds' % (time.perf_counter() - started), file=output)
                    LOG.info('%s', output.getvalue().rstrip())

    def _dispatch(self, method, args, kwargs, record):
        if method not in SUPPORTED_METHODS:
            if method in ('commit_session', 'get_md5_info'):
                raise UnsupportedContract('Deprecated production API is excluded: ' + method)
            raise UnsupportedContract(f"TACTIC method '{method}' has not been migrated yet")
        function = getattr(self, method)
        kwargs = kwargs or {}
        # Validate argument shape before executing any authentication mutation.
        key = getattr(function, '__func__', function)
        signature = self._signatures.get(key)
        if signature is None:
            signature = inspect.signature(function)
            self._signatures[key] = signature
        bound = signature.bind(*args, **kwargs)
        if record['log_enabled']:
            record['arguments'] = log_arguments({name: value for name, value in bound.arguments.items()
                if method != 'missing_method' or name != 'args'})
            record['method'] = key
        if method in ("get_ticket", "get_ticket_data", "fast_ping", "missing_method"):
            return function(*args, **kwargs)
        if method == 'set_palette':
            # The source signature has no ticket. Its palette ends with this request.
            with request_context(RequestContext(self.store, None, 'admin')):
                return function(*args, **kwargs)
        ticket = bound.arguments["ticket"]
        if isinstance(ticket, str):
            project, _, token = ticket.partition(":")
            ticket = {"ticket": token if token else project, "project": project if token else None}
        if not isinstance(ticket, dict):
            raise AuthenticationError("Invalid or expired ticket")
        if record['log_enabled']:
            token = ticket.get('ticket')
            if isinstance(token, str):
                record['ticket'] = token.replace('\r', '\\r').replace('\n', '\\n')
        if ticket.get("site") or ticket.get("language", "python") != "python":
            raise UnsupportedContract("Only the single-site Python ticket contract is migrated")
        login, state_xml = self.auth.validate(ticket.get("ticket"), return_state=True)
        transaction_id = None
        if state_xml:
            from pyasm.common import Xml
            state_data = Xml(state_xml)
            if state_data.get_root_node().tag != 'state':
                raise ValueError('Expected state XML root')
            transaction_id = state_data.get_value('state/transaction')
            if not ticket.get('project'):
                ticket = dict(ticket, project=state_data.get_value('state/project') or 'admin')
        project = ticket.get('project') or 'admin'
        record.update(user=login, project=project if isinstance(project, str) else type(project).__name__)
        context = RequestContext(self.store, login, ticket.get("project") or "admin")
        with request_context(context):
            from pyasm.common import Container
            Container.put('Api:environ', record.get('environ', {}))
            self.auth.bind_security(login, ticket.get("ticket"))
            if not Project.get():
                raise AuthenticationError("Project unavailable")
            # Original get_simple_cmd starts its timer after ApiXMLRPC.init.
            # The full request, including authentication, stays visible separately.
            record['method_started'] = time.perf_counter()
            self.check_method_access(method, command=bound.arguments.get('class_name'))
            checkin = self.checkin_write_scope(method, bound.arguments)
            if checkin is not None:
                Container.put('Checkin:writing', checkin)
            # ponytail: reader eval stays read-only until non-admin Command/SQL writes are migrated.
            create_directory = method in ('get_preallocated_path', 'get_virtual_snapshot_path') and bound.arguments.get('mkdirs', method == 'get_preallocated_path')
            if create_directory and not Environment.get_security().is_admin():
                raise SecurityException('Repository directory creation currently requires administrator access')
            if method in WRITE_METHODS or create_directory or (method in ('eval', 'query', 'fast_query', 'get_all_children', 'query_snapshots') and Environment.get_security().is_admin()):
                from pyasm.web.api_xmlrpc import ApiClientCmd
                from pyasm.command import Command
                cmd = ApiClientCmd()
                cmd.api = self
                cmd.function_name = method
                cmd.arguments = list(args[1:])
                # This transport runs locally; remote queues are not enabled.
                cmd.get_transaction().set_sync(False)
                explicit_replay_ticket = method in ('undo', 'redo') and bound.arguments.get('transaction_ticket')
                if state_xml and method != 'start' and not explicit_replay_ticket:
                    def execute():
                        from pyasm.search import TransactionState, TransactionLog, DbContainer
                        from pyasm.search.transaction import Transaction
                        transaction = Transaction.get()
                        sql = DbContainer.get(self.store.get_db_resource())
                        transaction.register_database(sql)
                        sql.lock_transaction_state(ticket['ticket'])
                        state = TransactionState.get_by_ticket(ticket['ticket'])
                        log_id = state.get_state('transaction') if state else None
                        if transaction_id and str(log_id) != str(transaction_id):
                            raise ValueError('Client transaction was closed before this request')
                        if log_id and method not in ('start', 'finish', 'abort', 'set_state', 'set_project', 'undo', 'redo', 'execute_transaction'):
                            log = TransactionLog.get_by_id(int(log_id))
                            if not log or log.get_value('login') != login or log.get_value('type') != 'undo':
                                raise SecurityException('Transaction does not belong to the current user or is closed')
                            transaction.set_transaction(log)
                            transaction.set_title(log.get_value('title'))
                            transaction.set_description(log.get_value('description'))
                        return function(*args, **kwargs)
                    cmd.execute = execute
                else:
                    cmd.execute = lambda: function(*args, **kwargs)
                return Command.execute_cmd(cmd)
            return function(*args, **kwargs)

    def checkin_write_scope(self, method, arguments):
        if method not in ('upload_file', 'simple_checkin', 'group_checkin', 'add_file', 'add_group',
                          'create_snapshot', 'lock_sobject', 'unlock_sobject', 'set_current_snapshot'):
            return None
        parent = None
        if method != 'upload_file':
            if method in ('simple_checkin', 'group_checkin', 'create_snapshot', 'lock_sobject', 'unlock_sobject'):
                key = arguments['search_key']
                try:
                    parent = self._sobject(key[0] if isinstance(key, list) else key)
                except LookupError:
                    if not Environment.get_security().is_admin():
                        raise SecurityException('Check-in requires a visible parent') from None
                    raise
            else:
                from pyasm.biz import Snapshot
                code = arguments['snapshot_code']
                snapshot = Snapshot.get_by_code(code.get('code') if isinstance(code, dict) else code)
                if snapshot is None:
                    raise LookupError('Snapshot does not exist')
                parent = snapshot.get_sobject()
                if parent is None:
                    raise SecurityException('Check-in requires a visible snapshot parent')
            if not Environment.get_security().is_admin() and (
                    arguments.get('mode') not in (None, '', 'upload', 'uploaded', 'manual', 'create') or
                    arguments.get('checkin_cls', 'pyasm.checkin.FileCheckin') != 'pyasm.checkin.FileCheckin'):
                raise SecurityException('Ordinary API check-in requires ticket uploads and native check-in classes')
        return {'parent': parent}

    @staticmethod
    def check_method_access(method, command=None):
        from pyasm.common import Config
        if Config.get_value('security', 'api_method_restricted') == 'true' and not Environment.get_security().check_access('api_method', method, 'allow', default='allow'):
            raise SecurityException('Access denied')
        if method == 'class_exists' and not Environment.get_security().is_admin():
            raise SecurityException('Class lookup currently requires administrator access')
        if method not in WRITE_METHODS and method not in ('eval', 'get_preallocated_path', 'get_virtual_snapshot_path', 'class_exists'):
            return
        chat_call = Container.get('Chat:writing') and method in (
            'insert', 'update', 'update_multiple', 'delete_sobject', 'log_message', 'connect_sobjects')
        object_call = method in ('insert', 'update', 'update_multiple', 'insert_multiple', 'insert_update',
                                 'get_unique_sobject', 'retire_sobject', 'reactivate_sobject', 'clone_sobject',
                                 'add_instance', 'remove_instance', 'delete_sobject', 'create_task', 'create_note', 'call_pipeline_event', 'execute_python_script', 'upload_file', 'simple_checkin', 'group_checkin', 'add_file', 'add_group', 'create_snapshot', 'lock_sobject', 'unlock_sobject', 'set_current_snapshot', 'checkout', 'undo', 'redo')
        browser_checkin = method == 'execute_cmd' and command in ('tactic.command.browser_checkin_cmd.BrowserCheckinCmd',
            'tactic.command.checkin_queue_cmd.SubmitCheckinChunkCmd', 'tactic.command.checkin_queue_cmd.CancelCheckinBatchCmd',
            'tactic.command.file_project_cmd.FileProjectCmd')
        table_call = method == 'execute_cmd' and command in (
            'tactic.ui.table.task_workspace.TaskWorkspaceCmd',
            'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd',
            'tactic.ui.table.task_inspector.TaskInspectorCmd',
            'tactic.ui.table.task_inspector.TaskTableEditCmd',
            'tactic.ui.table.task_schedule.TaskScheduleCmd',
            'tactic.ui.widget.discussion_wdg.DiscussionReadCmd',
            'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
            'tactic.ui.panel.custom_url_cmd.CustomUrlCmd',
            'tactic.ui.table.CustomLayoutReadCmd',
            'tactic.ui.panel.dashboard_form_cmd.DashboardFormCmd',
            'tactic.ui.panel.EditCmd', 'tactic.ui.panel.EditMultipleCmd',
            'tactic.ui.table.TableCellEditCmd', 'tactic.ui.table.NestedTableReadCmd',
            'tactic.ui.table.TableDependencyReadCmd', 'tactic.ui.table.TableConnectionRemoveCmd',
            'tactic.ui.table.TableParentGroupCmd', 'tactic.ui.table.TableSnapshotAppendCmd',
            'tactic.ui.table.TableSnapshotFilesCmd', 'tactic.ui.table.TableObjectStatusCmd',
            'tactic.ui.table.DropElementEditCmd', 'tactic.ui.table.TableTimeEditCmd',
            'tactic.command.sobject_link_cmd.SObjectLinkCmd')
        if method in WRITE_METHODS and not Environment.get_security().is_admin() and not (chat_call or object_call or browser_checkin or table_call or method == 'log'):
            raise SecurityException('API writes currently require administrator access')



    def missing_method(self, func, args):
        # Original BaseApiXMLRPC diagnostic used by the unchanged SDK fallback.
        return False

    def set_palette(self, palette):
        from pyasm.web import Palette
        Palette.push_palette(palette)

    @staticmethod
    def _init_web(ticket, values=None):
        from pyasm.web import WebContainer, Web
        WebContainer.set_web(Web(values))

    def get_widget(self, ticket, class_name, args={}, values={}, libraries={}, interaction={}):
        from pyasm.common import Config, Common
        from pyasm.security.security import _require_admin
        from pyasm.web import Widget
        _require_admin()
        if not all(isinstance(value, dict) for value in (args, values, libraries, interaction)):
            raise ValueError('Widget args, values, libraries and interaction must be dictionaries')
        if not isinstance(class_name, str):
            raise ValueError('Widget class must be a qualified name')
        if class_name.startswith('$'):
            import re
            if not re.fullmatch(r'\$[a-zA-Z0-9]+', class_name):
                raise SecurityException('Invalid widget key')
            path = Path(Environment.get_tmp_dir(include_ticket=True)) / ('widget_key_' + class_name[1:] + '.txt')
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('login') != Environment.get_user_name():
                raise SecurityException('Widget key belongs to another user')
            class_name, inputs = data['method'], data['inputs']
            if Config.get_value('security', 'api_widget_restricted') == 'true':
                for name, value in args.items():
                    expected = inputs.get(name)
                    if isinstance(expected, str):
                        expected = expected.replace('&amp;', '&')
                    if expected != '__WIDGET_UNKNOWN__' and expected != value:
                        raise SecurityException('Unexpected widget input: ' + name)
        elif Config.get_value('security', 'api_widget_restricted') == 'true':
            access_key = {'key': 'widget/' + class_name, 'project': Project.get_project_code()}
            if not Environment.get_security().check_access('builtin', access_key, 'allow'):
                raise SecurityException('Widget access denied; use a widget key')
        self._init_web(ticket, values)
        try:
            widget_class = Common.resolve_class(class_name)
        except (ImportError, AttributeError) as error:
            raise UnsupportedContract('Native HTML widget class is unavailable: ' + class_name) from error
        if not isinstance(widget_class, type) or not issubclass(widget_class, Widget):
            raise ValueError('Must be derived from Widget')
        if libraries.get('spt_help'):
            raise UnsupportedContract('Native HTML HelpWdg is not migrated')
        Container.put('JSLibraries', libraries)
        widget = widget_class(**args)
        Container.put('request_top_wdg', widget)
        return widget.get_buffer_display()

    def set_application_state(self, ticket, key, panel_name, widget_class, options, values={}):
        from pyasm.common import Common
        from pyasm.web import WebEnvironment
        if key != 'top_layout':
            raise ValueError('layout [%s] not supported' % key)
        self._init_web(ticket)
        widget = Common.create_from_class_path(WebEnvironment.get_top_class_name())
        widget.set_state(panel_name, widget_class, options, values)
        return True

    def get_column_widgets(self, ticket, search_type, search_keys, element_name):
        from pyasm.widget import WidgetConfig, WidgetConfigView
        from pyasm.search import SearchKey
        from tactic.ui.panel import TableLayoutWdg
        from xml.etree import ElementTree as ET
        self._init_web(ticket)
        root = ET.Element('config')
        ET.SubElement(ET.SubElement(root, 'table'), 'element', name=element_name)
        configx = WidgetConfig.get(view='table', xml=ET.tostring(root, encoding='unicode'))
        config = WidgetConfigView.get_by_search_type(search_type, 'table')
        # Do not modify the shared, request-cached view for the next column call.
        config = WidgetConfigView(search_type, 'table', [configx] + list(config.configs))
        sobjects = []
        if search_keys:
            if search_keys[0].endswith('id=-1'):
                search_keys = search_keys[1:]
            # Retain the source's empty/single-key result; fixing it changes the contract.
            if len(search_keys) > 1:
                sobjects = SearchKey.get_by_search_keys(search_keys)
                if len(sobjects) != len(search_keys):
                    raise LookupError('Not all column objects are accessible')
        table = TableLayoutWdg(search_type=search_type, view='table', config=config)
        table.render_column_cells = True
        table.set_sobjects(sobjects)
        for widget in table.widgets:
            if widget.get_name() == element_name:
                table.widgets = [widget]
                break
        else:
            raise ValueError('Element name [%s] not in view [table]' % element_name)
        table.get_display()
        return [[cell.get_buffer_display() for cell in row.widgets[2:]] for row in table.table.rows]

    def execute_js_script(self, ticket, script_path, kwargs={}):
        from tactic.command import JsCmd
        from pyasm.command import Command
        if script_path:
            from tactic_stream.server.script_access import query_runner_access
            from pyasm.biz import Project
            denied = json.loads(query_runner_access(Project.get_project_code()))['denied']
            if '*' in denied or script_path in denied:
                raise SecurityException('Your groups cannot run this script: ' + script_path)
        cmd = JsCmd(script_path=script_path, **kwargs)
        Command.execute_cmd(cmd)
        return {'status': 'OK', 'description': cmd.get_description(), 'info': cmd.get_info()}

    def send_rest_request(self, ticket, method, url, params={}):
        from urllib.error import HTTPError
        from urllib.parse import urlencode, urlsplit, urlunsplit
        from urllib.request import Request, urlopen
        from pyasm.security.security import _require_admin
        _require_admin()
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            raise ValueError('REST requests require an HTTP or HTTPS URL')
        if parts.username is not None or parts.password is not None:
            raise UnsupportedContract('REST URL credentials are not migrated')
        if isinstance(params, (str, bytes)):
            encoded = params.decode('utf-8') if isinstance(params, bytes) else params
        else:
            pairs = params.items() if isinstance(params, dict) else params or ()
            pairs = [(key, item) for key, value in pairs
                     for item in (value if isinstance(value, (list, tuple)) else [value]) if item is not None]
            encoded = urlencode(pairs, doseq=True)
        if method.lower() == 'post':
            request = Request(url, data=encoded.encode('utf-8'))
        else:
            query = '&'.join(value for value in (parts.query, encoded) if value)
            request = Request(urlunsplit(parts._replace(query=query)))
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error  # Source returns JSON even for HTTP error statuses.
        with response:
            data = response.read()
            charset = response.headers.get_content_charset()
            return json.loads(data.decode(charset) if charset else data)

    def execute_cmd(self, ticket, class_name, args={}, values={}, use_transaction=True):
        from pyasm.common import Common, Config, Container
        from pyasm.command import Command
        if not isinstance(values, dict):
            raise ValueError('Command form values must be a dictionary')
        if isinstance(args, str):
            args = json.loads(args)
        if not isinstance(args, dict):
            raise ValueError('Command args must be a dictionary or JSON object')
        args = dict(args)
        key = None
        if not isinstance(class_name, str):
            raise ValueError('Command class must be a qualified name or key')
        if class_name.startswith('$'):
            import re
            if not re.fullmatch(r'\$[a-zA-Z0-9]+', class_name):
                raise SecurityException('Invalid command key')
            directory = Path(Environment.get_tmp_dir(include_ticket=True)).resolve()
            path = directory / ('key_' + class_name[1:] + '.txt')
            if not path.resolve().is_relative_to(directory):
                raise SecurityException('Command key must stay inside its ticket directory')
            if not path.is_file():
                raise ValueError('Command key not valid')
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('login') != Environment.get_user_name():
                raise SecurityException('Command key belongs to another user')
            class_name = data.get('class_name')
            if not isinstance(class_name, str) or not isinstance(data.get('kwargs') or {}, dict):
                raise ValueError('Invalid command key contents')
            args.update(data.get('kwargs') or {})
            key = path
        if Config.get_value('security', 'api_cmd_restricted') == 'true' and not Environment.get_security().check_access('api_cmd', class_name, 'allow', default='allow'):
            raise SecurityException('Access denied')
        command_class = Common.resolve_class(class_name)
        if not inspect.isclass(command_class) or not issubclass(command_class, Command):
            raise TypeError('Cannot execute command. Must be derived from Command class.')
        from pyasm.web import WebContainer, Web
        previous_web = Container.get('WebContainer::web')
        WebContainer.set_web(Web(values))
        try:
            cmd = command_class(**{str(name): value for name, value in args.items()})
            if cmd.requires_key() and key is None:
                raise SecurityException('Key required for this command.')
            if not cmd.can_run(source='api'):
                raise SecurityException('Command [%s] cannot run from the API.' % class_name)
            if use_transaction:
                Command.execute_cmd(cmd)
            else:
                # The outer API Command still owns rollback, as in the source decorator.
                cmd.execute()
            return {'status': 'OK', 'description': cmd.get_description(), 'info': cmd.get_info()}
        finally:
            Container.put('WebContainer::web', previous_web)

    def execute_python_script(self, ticket, script_path, kwargs={}):
        from pyasm.common import Config
        from tactic.command import PythonCmd
        if not isinstance(script_path, (str, type(None))) or not isinstance(kwargs, dict):
            raise ValueError('A script path and dictionary arguments are required')
        if script_path:
            from tactic_stream.server.script_access import query_runner_access
            from pyasm.biz import Project
            denied = json.loads(query_runner_access(Project.get_project_code()))['denied']
            if '*' in denied or script_path in denied:
                raise SecurityException('Your groups cannot run this script: ' + script_path)
        if not script_path and not (kwargs.get('code') or kwargs.get('file_path')):
            raise ValueError('A saved script path, inline code or file path is required')
        for name in ('code', 'file_path'):
            if kwargs.get(name) and not isinstance(kwargs[name], str):
                raise ValueError('Script code and file path must be strings')
        if Config.get_value('security', 'api_cmd_restricted') == 'true' and not Environment.get_security().check_access('api_cmd', 'tactic.command.PythonCmd', 'allow', default='allow'):
            raise SecurityException('Access denied')
        from pyasm.command import Command
        cmd = PythonCmd(script_path=script_path, **kwargs)
        Command.execute_cmd(cmd)
        return {'status': 'OK', 'description': cmd.get_description(), 'info': cmd.get_info()}

    def eval(self, ticket, expression, search_keys=[], mode=None, single=False, vars={}, show_retired=False):
        # Original ApiXMLRPC.eval: roots, parser modes and Python transport envelope.
        from pyasm.biz import ExpressionParser
        from pyasm.search import SObject
        if not isinstance(expression, str) or not isinstance(vars, dict):
            raise ValueError('An expression string and dictionary variables are required')
        keys = [search_keys] if isinstance(search_keys, (str, dict)) else search_keys
        sobjects = [self._sobject(key) for key in keys] if keys else None
        with self._expression_access():
            results = ExpressionParser().eval(expression, sobjects, mode=mode, single=single,
                                              vars=vars, show_retired=show_retired)
            from pyasm.security import Site
            if isinstance(results, Site) or (isinstance(results, list) and any(isinstance(obj, Site) for obj in results)):
                raise UnsupportedContract('Site is a provider, not a database record; read its fields with @GET')
            if isinstance(results, list) and results and isinstance(results[0], SObject):
                results = [self._record(obj) for obj in results]
            elif isinstance(results, SObject):
                results = self._record(results)
            elif isinstance(results, Search):
                raise UnsupportedContract('Expression Search objects require a local core call')
            return results if self.protocol in ('json', 'local') else str(results)

    @contextmanager
    def _expression_access(self):
        previous_read = Container.get('Expression:check_record_access')
        previous_write = Container.get('Expression:check_method_access')
        Container.put('Expression:check_record_access', check_record_access)
        Container.put('Expression:check_method_access', self.check_method_access)
        try:
            yield
        finally:
            Container.put('Expression:check_record_access', previous_read)
            Container.put('Expression:check_method_access', previous_write)

    def get_ticket(self, login_name, password, site=None):
        return self.auth.get_ticket(login_name, password, site)

    def get_ticket_data(self, login_name, password, site=None):
        return self.auth.get_ticket_data(login_name, password, site)

    def fast_ping(self, ticket):
        # Original fast_ping is explicitly public and does not initialize a ticket.
        return "OK"

    def ping(self, ticket):
        return "OK"

    @staticmethod
    def _search(search_type):
        check_record_access(SearchKey.extract_base_search_type(search_type))
        return Search(search_type)

    def log(self, ticket, level, message, category="default"):
        '''Log a message in the logging queue

        @params
        ticket - authentication ticket
        level - debug level ....
        message - freeform string describing the entry
        '''
        from pyasm.biz import DebugLog
        log = DebugLog.log(level,message,category)
        return True

    def undo(self, ticket, transaction_ticket=None, transaction_id=None, ignore_files=False):
        from pyasm.command import Command, UndoCmd
        if transaction_ticket:
            state = self._transaction_state(transaction_ticket)
            state.restore_state()
            transaction_id = state.get_state('transaction') or transaction_id
        cmd = UndoCmd(ignore_files=ignore_files)
        if transaction_id:
            cmd.set_transaction_id(transaction_id)
        Command.execute_cmd(cmd)
        return True

    def redo(self, ticket, transaction_ticket=None, transaction_id=None):
        from pyasm.command import Command, RedoCmd
        if transaction_ticket:
            state = self._transaction_state(transaction_ticket)
            state.restore_state()
            transaction_id = state.get_state('transaction') or transaction_id
        cmd = RedoCmd()
        if transaction_id:
            cmd.set_transaction_id(transaction_id)
        Command.execute_cmd(cmd)
        return True

    def execute_transaction(self, ticket, transaction_xml, file_mode=None):
        from tactic.command import RunTransactionCmd
        cmd = RunTransactionCmd(transaction_xml=transaction_xml, file_mode=file_mode)
        cmd.execute()
        return {'status': 'OK'}

    def _transaction_state(self, ticket_key=None):
        from pyasm.search import TransactionState, Transaction, DbContainer
        from pyasm.security import Ticket
        explicit_ticket = ticket_key is not None
        ticket_key = ticket_key or Environment.get_security().get_ticket_key()
        saved = Ticket.get_by_valid_key(ticket_key)
        if not saved or saved.get_value('login') != Environment.get_user_name():
            raise SecurityException('Transaction ticket does not belong to the current user')
        if explicit_ticket:
            transaction = Transaction.get()
            sql = DbContainer.get(self.store.get_db_resource())
            transaction.register_database(sql)
            sql.lock_transaction_state(ticket_key)
        state = TransactionState.get_by_ticket(ticket_key)
        if not state:
            raise ValueError('No transaction state for this ticket')
        return state

    def set_state(self, ticket, name, value):
        return self._set_state(ticket, name, value)

    def _set_state(self, ticket, name, value):
        from pyasm.search import Transaction, TransactionLog
        state = self._transaction_state()
        if name == 'project' and not Project.get_by_code(value):
            raise ValueError('Invalid project code [%s]' % value)
        if name == 'transaction' and value:
            log = TransactionLog.get_by_id(int(value))
            if not log or log.get_value('login') != Environment.get_user_name():
                raise SecurityException('Transaction does not belong to the current user')
        Transaction.get().set_record(False)
        state.set_state(name, value)
        state.commit(triggers=False, log_transaction=False)
        return True

    def set_project(self, ticket, project):
        return self._set_state(ticket, 'project', project)

    def start(self, ticket, project_code, title='', description=None, transaction_ticket=''):
        from pyasm.common import Common
        from pyasm.search import Transaction, TransactionLog, TransactionState, DbContainer
        from pyasm.security import Ticket
        transaction = Transaction.get()
        title = title or 'No title'
        if self.protocol == 'local':
            if transaction:
                transaction.set_description(description)
                transaction.set_title(title)
            return Environment.get_security().get_ticket_key()
        if not Project.get_by_code(project_code):
            raise ValueError('Invalid project code [%s]' % project_code)
        if transaction_ticket:
            sql = DbContainer.get(self.store.get_db_resource())
            transaction.register_database(sql)
            sql.lock_transaction_state(transaction_ticket)
            saved = Ticket.get_by_key(transaction_ticket)
            if saved and saved.get_value('login') != Environment.get_user_name():
                raise SecurityException('Transaction ticket does not belong to the current user')
            if saved and not Ticket.get_by_valid_key(transaction_ticket):
                raise SecurityException('Transaction ticket has expired')
            state = TransactionState.get_by_ticket(transaction_ticket)
            if state and state.get_state('transaction'):
                raise ValueError('Client transaction is already active')
        else:
            transaction_ticket = Common.generate_random_key()
            saved = state = None
        from pyasm.checkin.repo import _check_file_name
        _check_file_name(transaction_ticket)
        transaction.set_record(False)
        Project.set_project(project_code)
        if not saved:
            Ticket.create(transaction_ticket, Environment.get_user_name(), interval='7 day')
        if state is None:
            state = TransactionState.create(transaction_ticket)
        state.reset_state()
        log = TransactionLog.create('pyasm.web.api_xmlrpc.ApiClientCmd',
            '<transaction/>', description or 'Client API (No description)', title)
        state.set_state('transaction', log.get_id())
        state.set_state('project', project_code)
        state.commit(triggers=False, log_transaction=False)
        # The source copied uploads using a dict as a path component. Resolve
        # the authenticated key and retain the source's copy-only semantics.
        from pyasm.search import FileUndo
        source = Path(Environment.get_upload_dir())
        destination = source.parent / transaction_ticket
        if source != destination and source.is_dir():
            for path in source.iterdir():
                target = destination / path.name
                if path.is_file() and not target.exists():
                    FileUndo.mkdir(str(destination))
                    FileUndo.copy(str(path), str(target))
        return transaction_ticket

    def finish(self, ticket, description=''):
        if self.protocol == 'local':
            return True
        from pyasm.search import Transaction, TransactionLog
        Transaction.get().set_record(False)
        state = self._transaction_state()
        log_id = state.get_state('transaction')
        if log_id:
            log = TransactionLog.get_by_id(int(log_id))
            if not log or log.get_value('login') != Environment.get_user_name():
                raise SecurityException('Transaction does not belong to the current user')
            from pyasm.common import Common, Xml
            data = log.get_value('transaction')
            xml = Xml(Common.decompress_transaction(data) if data.startswith('zlib:') else data)
            if xml.get_root_node().tag != 'transaction':
                raise ValueError('Expected transaction XML root')
            if not xml.get_nodes('transaction/*'):
                log.delete(triggers=False, log=False)
            else:
                if description:
                    log.set_value('description', description)
                    log.commit(triggers=False, log_transaction=False)
                TransactionLog.create_sobject_log(log)
        project = state.get_state('project')
        state.reset_state()
        state.set_state('project', project)
        state.commit(triggers=False, log_transaction=False)
        return True

    def abort(self, ticket, ignore_files=False):
        from pyasm.command import Command, CommandExitException, UndoCmd
        from pyasm.search import Transaction
        if self.protocol == 'local':
            raise CommandExitException('aborted.')
        Transaction.get().set_record(False)
        state = self._transaction_state()
        project = state.get_state('project')
        state.restore_state()
        log_id = state.get_state('transaction')
        if log_id:
            cmd = UndoCmd(ignore_files=ignore_files)
            cmd.set_transaction_id(int(log_id))
            if cmd.transaction_log.get_value('login') != Environment.get_user_name():
                raise SecurityException('Transaction does not belong to the current user')
            Command.execute_cmd(cmd)
        state.reset_state()
        state.set_state('project', project)
        state.commit(triggers=False, log_transaction=False)
        return True



    def query(self, ticket, search_type, filters=None, columns=None, order_bys=None,
              show_retired=False, limit=None, offset=None, single=False, distinct=None,
              return_sobjects=False, parent_key=None):
        if return_sobjects and self.protocol != 'local':
            raise UnsupportedContract("Local SObjects are not supported by the XML-RPC transport")
        search = self._search(search_type)
        with self._expression_access():
            search.add_op_filters(filters or [])
        if parent_key:
            search.add_parent_filter(self._sobject(parent_key))
        if distinct:
            search.add_column(distinct, distinct=True)
        for order in [order_bys] if isinstance(order_bys, str) else order_bys or []:
            search.add_order_by(order)
        if search.database == 'sthpw':
            for stype in PROTECTED_TYPES:
                if stype.split('/')[1] in search.join_columns:
                    check_record_access(stype)
        # Original ApiXMLRPC treats zero limits/offsets as unspecified.
        if limit:
            search.set_limit(limit)
        if offset:
            search.set_offset(offset)
        if single:
            search.set_limit(1)
        if (columns and not distinct and not return_sobjects and not search.joins and
                not search.select.columns and not search.select.group_bys and
                not search.select.distinct and not search.distinct and
                search.search_type_obj.get_class() in ('pyasm.search.SObject', 'pyasm.search.search.SObject')):
            # Preserve retirement, ordering and identity while avoiding unrelated large fields.
            for column in dict.fromkeys([*columns, 'id', 'code', 's_status']):
                if column in search.columns:
                    search.add_column(column)
        search.set_show_retired(show_retired)
        sobjects = search.get_sobjects()
        if return_sobjects:
            return (sobjects[0] if sobjects else {}) if single else sobjects
        search_keys = (SearchKey.get_by_sobjects(sobjects) if not distinct and
                       search.search_type_obj.get_class() in ('pyasm.search.SObject', 'pyasm.search.search.SObject')
                       else None)
        results = []
        for index, obj in enumerate(sobjects):
            data = obj.get_data()
            if obj.get_base_search_type() == 'sthpw/snapshot' and data.get('repo') == 'default':
                data['repo'] = 'base'
            if columns:
                data = {name: data.get(name) for name in columns}
            if not distinct:
                data["__search_key__"] = search_keys[index] if search_keys is not None else obj.get_search_key()
            results.append(data)
        # Python TacticServerStub expects a Python-literal string, including None/False.
        result = (results[0] if results else {}) if single else results
        return result if self.protocol in ('json', 'local') else repr(result)

    def get_column_info(self, ticket, search_type):
        return SearchType.get_column_info(search_type)

    def get_column_names(self, ticket, search_type):
        return Search(search_type).get_columns()

    def get_table_info(self, ticket, search_type):
        return self.store.tables(Project.get_db_resource_by_search_type(search_type))

    @staticmethod
    def _record(obj, use_id=False, check_security=True, columns=None):
        if not obj:
            return {}
        if check_security:
            check_record_access(obj.get_base_search_type())
        result = obj.get_data()
        if isinstance(obj, SearchType) and columns is None:
            result['__record_read__'] = obj.get_record_read_options()
        if obj.get_base_search_type() == 'sthpw/snapshot' and result.get('repo') == 'default':
            result['repo'] = 'base'
        if 'metadata' in result:
            # Source reads metadata but returns the original stored field.
            obj.get_metadata_dict()
        if columns:
            result = {name: result.get(name) for name in columns}
        # Original _get_sobjects_dict Python 3 scalar conversions.
        for column, value in result.items():
            if column.startswith('__') or column == 'metadata':
                continue
            if isinstance(value, (datetime, Decimal)):
                result[column] = str(value)
        result.update(__search_key__=obj.get_search_key(use_id), __search_type__=obj.get_search_type())
        return result

    @staticmethod
    def _get_sobject_dict(sobject, columns=None, use_id=False, *, check_security=True):
        return ApiXMLRPC._record(sobject, use_id, check_security, columns)

    @staticmethod
    def _get_sobjects_dict(sobjects, columns=None, use_id=False, *, check_security=True):
        """Original Python 3 record conversion, shared with the local SDK."""
        results = []
        checked = set()
        for sobject in sobjects or []:
            if not sobject:
                continue
            search_type = sobject.get_base_search_type()
            if check_security and search_type not in checked:
                check_record_access(search_type)
                checked.add(search_type)
            # The source batch key helper assumes one type/project. These
            # objects can be mixed; use_id and projection must also be honored.
            result = ApiXMLRPC._record(sobject, use_id, check_security=False, columns=columns)
            results.append(result)
        return results

    def get_by_code(self, ticket, search_type, code, x=None):
        search = self._search(search_type)
        search.add_filter("code", code)
        search.set_show_retired(True)
        return self._record(search.get_sobject())

    def get_by_search_key(self, ticket, search_key):
        if isinstance(search_key, list):
            return [self.get_by_search_key(ticket, key) for key in search_key]
        return self._record(self._sobject(search_key))

    def _sobject(self, search_key):
        if isinstance(search_key, dict):
            search_key = search_key.get("__search_key__")
        if not isinstance(search_key, str) or not search_key:
            raise ValueError("A search key is required")
        while '&amp;' in search_key:
            search_key = search_key.replace('&amp;', '&')
        base = search_key.split("?", 1)[0].split("|", 1)[0]
        check_record_access(base)
        obj = Search.get_by_search_key(search_key)
        if not obj:
            raise LookupError("SObject does not exist")
        return obj

    def get_related_types(self, ticket, search_type):
        return Schema.get().get_related_search_types(search_type)

    def get_parent(self, ticket, search_key, columns=[], show_retired=True):
        parent = self._sobject(search_key).get_parent(show_retired=show_retired)
        if not show_retired and parent and parent.is_retired():
            return {}
        return self._get_sobject_dict(parent, columns)

    def get_all_children(self, ticket, search_key, child_type, filters=[], columns=[]):
        self._search(child_type)
        search = self._sobject(search_key).get_all_children_search(child_type)
        with self._expression_access():
            search.add_op_filters(filters)
        return self._get_sobjects_dict(search.get_sobjects(), columns)

    def get_parent_type(self, ticket, search_key):
        return Schema.get().get_parent_type(search_key)

    def get_child_types(self, ticket, search_key):
        return Schema.get().get_child_types(search_key)

    def get_types_from_instance(self, ticket, instance_type):
        return Schema.get().get_types_from_instance(instance_type)

    @staticmethod
    def _write_options(search_type, metadata, parent_key, info, collection_key=None):
        base = SearchKey.extract_base_search_type(search_type)
        if Container.get('Chat:writing') and base not in (
                'sthpw/message', 'sthpw/message_log', 'sthpw/subscription', 'sthpw/connection'):
            raise SecurityException('Chat operation cannot write other object types')
        from pyasm.search import SObject
        if base.startswith(('sthpw/', 'config/')) and base not in SObject.SECURITY_TYPES + SObject.BUSINESS_TYPES:
            raise UnsupportedContract('Public domain writes require the remaining persistence path')
        check_record_access(base)
        if metadata and not SearchType.column_exists(search_type, 'metadata'):
            raise UnsupportedContract('Search type has no metadata column: ' + search_type)
        if not isinstance(info, dict):
            raise ValueError('API command info must be a dictionary')

    def create_snapshot(self, ticket, search_key, context, snapshot_type="file", description="No description", is_current=True, level_key=None, is_revision=False, triggers=True):
        from pyasm.biz import Snapshot
        sobject = self._sobject(search_key[0] if isinstance(search_key, list) else search_key)
        if level_key:
            level = self._sobject(level_key[0] if isinstance(level_key, list) else level_key)
            level_type = level.get_search_type()
            level_id = level.get_id()
        else:
            level_type = level_id = None
        snapshot = Snapshot.create(sobject, snapshot_type=snapshot_type, context=context,
                                   description=description, is_current=is_current, level_type=level_type,
                                   level_id=level_id, is_revision=is_revision, triggers=triggers)
        return self._record(snapshot)

    def insert(self, ticket, search_type, data, metadata={}, parent_key=None, info={}, use_id=False, triggers=True, collection_key=None):
        self._write_options(search_type, metadata, parent_key, info, collection_key)
        if not isinstance(metadata, dict):
            raise ValueError('Insert metadata must be a dictionary')
        sobject = SearchType.create(search_type)
        for name, value in data.items():
            if name == 'metadata':
                # The source nested the entire column under another metadata key.
                sobject.add_metadata(value)
            else:
                sobject.set_value(name, value)
        for name, value in metadata.items():
            sobject.set_metadata_value(name, value)
        if parent_key:
            sobject.set_parent(self._sobject(parent_key))
        sobject.commit(triggers=triggers)
        self.set_sobject(sobject)
        self.update_info(info)
        if collection_key:
            sobject.add_to_collection(self._sobject(collection_key))
        return self._record(sobject, use_id=use_id, check_security=False)

    def update(self, ticket, search_key, data={}, metadata={}, parent_key=None, info={}, use_id=False, triggers=True):
        keys = search_key if isinstance(search_key, list) else [search_key]
        objects = [self._sobject(key) for key in keys]
        if isinstance(metadata, list):
            if len(metadata) != len(objects) or any(not isinstance(item, dict) for item in metadata):
                raise ValueError('Update metadata must contain one dictionary per search key')
        elif not isinstance(metadata, dict):
            raise ValueError('Update metadata must be a dictionary or a list of dictionaries')
        for index, sobject in enumerate(objects):
            cur_metadata = metadata[index] if isinstance(metadata, list) else metadata
            self._write_options(sobject.get_search_type(), cur_metadata, parent_key, info)
        results = []
        for index, sobject in enumerate(objects):
            cur_data = data[index] if isinstance(data, list) else data
            for name, value in cur_data.items():
                if name.startswith('__') and name.endswith('__'):
                    continue
                if name == 'metadata':
                    sobject.add_metadata(value)
                else:
                    sobject.set_value(name, value)
            cur_metadata = metadata[index] if isinstance(metadata, list) else metadata
            for name, value in cur_metadata.items():
                if name.startswith('__') and name.endswith('__'):
                    continue
                sobject.set_metadata_value(name, value)
            if parent_key:
                if index == 0:
                    resolved_parent = self._sobject(parent_key)
                sobject.set_parent(resolved_parent)
            sobject.commit(triggers=triggers)
            results.append(self._record(sobject, use_id=use_id, check_security=False))
        self.set_sobjects(objects)
        self.update_info(info)
        return results if isinstance(search_key, list) else results[0]

    def update_multiple(self, ticket, data, triggers=True):
        '''Update for several sobjects in one function call.  The
        data structure contains all the infon needed to update and is
        formated as follows:

        data = {
            search_key1: { column1: value1, column2: value2 }
            search_key2: { column1: value1, column2: value2 }
        }


        @params:
        ticket - authentication ticket
        data - data structure containing update information for all
            sobjects
        triggers - boolean to fire trigger on update

        @keyparam:
        data - a dictionary of name/value pairs which will be used to update
            the sobject defined by the search_key
            Note: this can also be an array.  Each data dictionary element in
            the array will be applied to the corresponding search key
        triggers - boolean to fire trigger on insert


        @return:
        a list of all the update sobjects

        '''

        if isinstance(data, str):
            data = json.loads(data)

        if not isinstance(data, dict) or any(not isinstance(row, dict) for row in data.values()):
            raise ValueError('data must map search keys to dictionaries')
        search_keys = list(data)
        use_id_list = []
        # auto detects use_id or not
        for search_key in search_keys:
            if '?id=' in search_key or '&id=' in search_key or '|' in search_key:
                use_id_list.append(True)
            else:
                use_id_list.append(False)

        sobjects = [self._sobject(key) for key in search_keys]

        if len(sobjects) < len(search_keys):
            raise ValueError('Not all search keys have equivalent sobjects in the system.')

        for sobject in sobjects:
            self._write_options(sobject.get_search_type(), {}, None, {})
        results = []

        for idx, sobject in enumerate(sobjects):
            search_key = sobject.get_search_key(use_id=use_id_list[idx])
            sobject_data = data[search_keys[idx]]
            if not sobject_data:
                print("search key [%s] does not exist in the system." %search_key)
                continue
            for key, value in sobject_data.items():
                sobject.set_value(key, value)
            sobject.commit(triggers=triggers)

            sobject_dict = self._record(sobject, use_id=use_id_list[idx])
            results.append(sobject_dict)

        return results

    def insert_multiple(self, ticket, search_type, data, metadata=[], parent_key=None, use_id=False, triggers=True):
        '''Insert for several sobjects in one function call.  The
        data structure contains all the infon needed to update and is
        formated as follows:

        data = [
            { column1: value1, column2: value2,  column3: value3 },
            { column1: value1, column2: value2,  column3: value3 }
        ]

        metadata =  [
            { color: blue, height: 180 },
            { color: orange, height: 170 }
        ]


        @params:
        ticket - authentication ticket
        data - a dictionary of name/value pairs which will be used to update
            the sobject defined by the search_key
            Note: this can also be an array.  Each data dictionary element in
            the array will be applied to the corresponding search key

        @keyparam:

        triggers - boolean to fire trigger on insert
        use_id - boolean to control if id is used in the search_key in returning sobject dict

        @return:
        a list of all the update sobjects

        '''

        if isinstance(data, str):
            data = json.loads(data)



        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        if not isinstance(data, list):
            raise ValueError('data must be a list')

        if metadata:
            if len(metadata) != len(data):
                raise ValueError('If specified, metadata length has to match data length [%s]'%len(data))
            if not isinstance(metadata, list):
                raise ValueError('metadata must be a list')

        results = []
        metadata_item = {}


        # they all share the same parent_key if exists
        for idx,  data_item in enumerate(data):
            if metadata:
                metadata_item = metadata[idx]

            result = self.insert(ticket, search_type, data_item, metadata=metadata_item, parent_key=parent_key, use_id=use_id, triggers=triggers)
            results.append(result)

        return results

    def insert_update(self, ticket, search_key, data={}, metadata={}, parent_key=None, info={}, use_id=False, triggers=True):

        '''insert if the entry does not exist, update otherwise

        @params:
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject.

        @keyparams:
        data - a dictionary of name/value pairs which will be used to update
            the sobject defined by the search_key
        parent_key - parent search_key
        info - a dictionary of info passed to ApiClientCmd
        use_id - use id in the returned search key
        triggers - boolean to fire trigger on insert

        @return
        a dictionary representing the sobject with its current data.
        '''
        # search to see if the search_key exits
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')
        if not isinstance(search_key, str) or not search_key:
            raise ValueError('A search key is required')
        self._write_options(SearchKey.extract_search_type(search_key), metadata, parent_key, info)
        sobjects = Search.get_by_search_key(search_key)

        # if it exists, the update
        if sobjects:
            return self.update(ticket, search_key, data, metadata, parent_key, info, use_id, triggers)

        # otherwise insert
        else:
            search_type = SearchKey.extract_search_type(search_key)
            # add code attribute
            code = SearchKey.extract_code(search_key)
            if code:
                data = dict(data, code=code)
            return self.insert(ticket, search_type, data, metadata, parent_key, info, use_id, triggers)

    def get_unique_sobject(self, ticket, search_type, data={}):
        '''This is a special convenience function which will query for an
        sobject and if it doesn't exist, create it.  It assumes that this
        object should exist and spares the developer the logic of having to
        query for the sobject, test if it doesn't exist and then create it.

        @param:
        search_type - the type of the sobject
        data - a dictionary of name/value pairs that uniquely identify this
            sobject

        @return:
        sobject - unique sobject matching the critieria in data
        '''
        self._write_options(search_type, {}, None, {})
        filters = []
        for key, value in data.items():
            # assume all items are 'name = value' expressions
            filter = [key, value]
            filters.append(filter)

        search = self._search(search_type)
        with self._expression_access():
            search.add_op_filters(filters)
        sobject = search.get_sobject()
        if not sobject:
            sobject = self.insert(ticket, search_type, data)

        if isinstance(sobject, dict):
            sobject_dict = sobject
        else: # for the queried sobject
            sobject_dict = self._record(sobject, use_id=False)

        return sobject_dict

    def retire_sobject(self, ticket, search_key):
        '''Invokes the retire method of the sobject

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject

        @return
        sobject - a dictionary that represents values of the sobject in the
            form name/value pairs
        '''
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject [%s] does not exist" % search_key)

        # retire this sobject
        self._write_options(sobject.get_search_type(), {}, None, {})
        sobject.retire()

        return self._record(sobject)

    def reactivate_sobject(self, ticket, search_key):
        '''Invokes the reactivate method of the sobject

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject

        @return
        sobject - a dictionary that represents values of the sobject in the
            form name/value pairs
        '''
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject [%s] does not exist" % search_key)

        # reactivate this sobject
        self._write_options(sobject.get_search_type(), {}, None, {})
        sobject.reactivate()

        return self._record(sobject)

    def clone_sobject(self, ticket, search_key, data={}):
        '''Clone an sobject.

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject
        data - a dictionary of data to update the sobject with

        @return
        sobject - a dictionary that represents values of the sobject in the
            form name/value pairs
        '''
        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject [%s] does not exist" % search_key)

        self._write_options(sobject.get_search_type(), {}, None, {})
        clone = sobject.clone()

        for name, value in data.items():
            clone.set_value(name, value)
        clone.commit()

        return self._record(clone)

    def create_note(self, ticket, search_key, note, process="publish", subcontext=None, user=None):
        '''Add a task for a particular sobject

        @params:
        ticket - authentication ticket
        search_key - the key identifying a type of sobject as registered in
                    the search_type table.
        note - detailed description of the task
        process - process that this task belongs to
        subcontext - the subcontex of the process (context = procsss/subcontext
        user - the user the note is attached to

        @return
        note that was created
        '''


        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)


        if subcontext:
            context = "%s/%s" % (process, subcontext)
        else:
            context = process

        note_obj = SearchType.create("sthpw/note")
        note_obj.set_value("process", process)
        note_obj.set_value("context", context)
        note_obj.set_parent(sobject)

        if note_obj:
            note_obj.set_value("note", note)

        note_obj.set_user(user)
        note_obj.commit()

        note_dict = self._record(note_obj)
        return note_dict

    def get_tasks(self, ticket, search_key, process=None):
        '''Get the tasks of an sobject

        ticket - authentication ticket
        search_key - the key identifying an sobject as registered in
                    the search_type table.

        @return:
        list of tasks
        '''

        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')
        sobject = self._sobject(search_key)

        search = Search("sthpw/task")
        search.add_parent_filter(sobject)
        if process:
            search.add_filter("process", process)
        tasks = search.get_sobjects()

        ret_tasks = []
        for task in tasks:
            task_dict = self._record(task)
            ret_tasks.append(task_dict)

        return ret_tasks

    def get_pipeline_xml(self, ticket, search_key):
        '''DEPRECATED: use get_pipeline_xml_info()
        method to retrieve the pipeline of a specific sobject.  The pipeline
        returned is an xml document.

        @params:
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject


        @return:
        string - xml of pipeline
        '''

        # get the sobject
        from pyasm.biz import Pipeline
        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        pipeline = Pipeline.get_by_sobject(sobject)
        if not pipeline:
            return "<pipeline/>"

        return pipeline.get_xml_value("pipeline").to_string()

    def get_pipeline_processes(self, ticket, search_key, recurse=False):
        '''DEPRECATED: use get_pipeline_processes_info()
        method to retrieve the pipeline of a specific sobject.  The pipeline
        returned is a dictionary

        @params:
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject

        @keyparams:
        recurse - boolean to control whether to display sub pipeline processes

        @return:
        process names of the pipeline or a dictionary if related_process is specified
        '''

        # get the sobject
        from pyasm.biz import Pipeline
        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        pipeline = Pipeline.get_by_sobject(sobject)
        if not pipeline:
            return []

        return pipeline.get_process_names(recurse=recurse)

    def get_preference(self, ticket, key):
        '''Get the users preference for this project

        @params
        ticket - authentication ticket
        key - unique key to identify preference

        @return
        current value of preference
        '''
        project_code = Project.get_project_code()

        from pyasm.biz import PrefSetting
        value = PrefSetting.get_value_by_key(key, project_code=project_code)
        return value

    def set_preference(self, ticket, key, value):
        '''Set the users preference for this project

        @params
        ticket - authentication ticket
        key - unique key to identify preference
        value - value to set the preference

        '''
        project_code = Project.get_project_code()

        from pyasm.biz import PrefSetting
        PrefSetting.create(key, value, project_code=project_code)

    def delete_sobject(self, ticket, search_key, include_dependencies=False):
        key = search_key[0] if isinstance(search_key, list) else search_key
        sobject = self._sobject(key)
        self._write_options(sobject.get_search_type(), {}, None, {})
        if include_dependencies:
            from tactic.ui.tools import DeleteCmd
            DeleteCmd(sobject=sobject, auto_discover=True).execute()
        else:
            sobject.delete()
        return self._record(sobject, check_security=False)

    def create_task(self, ticket, search_key, process="publish", subcontext=None, description=None,
                    bid_start_date=None, bid_end_date=None, bid_duration=None, assigned=None):
        parent = self._sobject(search_key)
        task = SearchType.create('sthpw/task')
        task.set_value('process', process)
        task.set_value('context', '%s/%s' % (process, subcontext) if subcontext else process)
        task.set_parent(parent)
        if bid_start_date and bid_end_date and bid_start_date > bid_end_date:
            raise ValueError('bid_start_date should be before bid_end_date.')
        for name, value in (('description', description), ('bid_start_date', bid_start_date),
                            ('bid_end_date', bid_end_date), ('bid_duration', bid_duration), ('assigned', assigned)):
            if value:
                task.set_value(name, value)
        task.commit()
        return self._record(task, check_security=False)

    def add_initial_tasks(self, ticket, search_key, pipeline_code=None, processes=[], skip_duplicate=True, offset=0, start_date=None):
        from pyasm.biz import Task
        parent = self._sobject(search_key)
        tasks = Task.add_initial_tasks(parent, pipeline_code=pipeline_code, processes=processes,
                                      skip_duplicate=skip_duplicate, start_offset=offset, start_date=start_date)
        return [self._record(task, check_security=False) for task in tasks]

    def get_message(self, ticket, key):
        return self._record(Search.get_by_code('sthpw/message', key))

    def get_messages(self, ticket, keys):
        search = Search('sthpw/message')
        search.add_filters('code', keys)
        return [self._record(message) for message in search.get_sobjects()]

    def log_message(self, ticket, key, message=None, status=None, category="default", log_history=True):
        from pyasm.command.message import log_message
        return log_message(key, message, status, category, log_history)


    def get_task_status_colors(self, ticket):
        '''Get all the colors for a task status

        ticket - authentication ticket

        @return:
        dictionary of colors
        '''
        from pyasm.biz import Task
        from pyasm.biz import Task
        return Task.get_status_colors()

    def get_input_tasks(self, ticket, search_key):
        '''Get the input tasks of a task based on the pipeline
        associated with the sobject parent of the task

        ticket - authentication ticket
        search_key - the key identifying an sobject as registered in
                    the search_type table.

        @return:
        list of input_tasks
        '''
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        task = self._sobject(search_key)
        if not task:
            raise LookupError("SObject for [%s] does not exist" % search_key)


        search_type = task.get_base_search_type()
        if search_type != "sthpw/task":
            raise ValueError("A task search key is required")

        input_tasks = task.get_input_tasks()

        ret_tasks = []
        for task in input_tasks:
            task_dict = self._record(task)
            ret_tasks.append(task_dict)

        return ret_tasks

    def get_output_tasks(self, ticket, search_key):
        '''Get the output tasks of a task based on the pipeline
        associated with the sobject parent of the task

        ticket - authentication ticket
        search_key - the key identifying an sobject as registered in
                    the search_type table.

        @return:
        list of output
        '''
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        task = self._sobject(search_key)
        if not task:
            raise LookupError("SObject for [%s] does not exist" % search_key)


        search_type = task.get_base_search_type()
        if search_type != "sthpw/task":
            raise ValueError("A task search key is required")

        input_tasks = task.get_output_tasks()

        ret_tasks = []
        for task in input_tasks:
            task_dict = self._record(task)
            ret_tasks.append(task_dict)

        return ret_tasks

    def create_pipeline(self, ticket, name, search_type, processes=[], process_types=[], description="", connected=True, xml=None):
        '''method to create a new pipeline.

        @params
        name - name of the pipeline
        processes - list of processes in the pipeline
        description - description of the pipeline

        '''
        from pyasm.biz import Pipeline
        from pyasm.common import Xml

        if xml:
            if isinstance(xml, str):
                xml_string = xml
                xml = Xml()
                xml.read_string(xml_string)
        else:
            xml = []
            xml.append('<?xml version="1.0" encoding="UTF-8"?>\n');
            xml.append('''<pipeline>''')
            if process_types and len(process_types) != len(processes):
                raise ValueError("One process type is required per process")
            for i, process in enumerate(processes):
                process_type = "manual"
                if process_types:
                    process_type = process_types[i]
                from xml.sax.saxutils import quoteattr
                xml.append('<process name=%s type=%s/>' % (quoteattr(process), quoteattr(process_type)))

            for i, process in enumerate(processes if connected else []):
                if i == len(processes)-1:
                    break

                next_process = processes[i+1]
                xml.append('<connect from=%s to=%s/>' % (quoteattr(process), quoteattr(next_process)))

            xml.append('''</pipeline>''')


            xml_string = "\n".join(xml)
            xml = Xml()
            xml.read_string(xml_string)

        pipeline = Pipeline.create(name, description, search_type, xml=xml)
        return self._record(pipeline)

    def get_pipeline_xml_info(self, ticket, search_key, include_hierarchy=False):
        '''method to retrieve the pipeline of a specific sobject.  The pipeline
        returned is an xml document.

        @params:
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject

        @keyparam:
        include_hierarchy - include a list of dictionary with key info on each process of the pipeline

        @return:
        dictionary - xml and the optional hierarachy info
        '''
        from pyasm.biz import Pipeline

        # get the sobject
        from pyasm.search import SearchKey
        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        pipeline = Pipeline.get_by_sobject(sobject)
        if not pipeline:
            return "<pipeline/>"

        main_data = {}

        main_data['xml'] =  pipeline.get_xml_value("pipeline").to_string()
        if include_hierarchy:
            processes = pipeline.get_processes()
            info = []
            for process in processes:
                data = {'process' : process.get_name()}
                data['task_pipeline'] = process.get_task_pipeline()
                data['output_contexts'] = pipeline.get_output_contexts(process.get_name())
                data['input_contexts'] = pipeline.get_input_contexts(process.get_name())

                input_processes = pipeline.get_input_processes(process)
                input_processes = [x.get_name() for x in input_processes]
                data['input_processes'] = input_processes
                output_processes = pipeline.get_output_processes(process)
                output_processes = [x.get_name() for x in output_processes]
                data['output_processes'] = output_processes

                info.append(data)
            main_data['hierarchy'] = info



        return main_data

    def get_pipeline_processes_info(self, ticket, search_key, recurse=False, related_process=None):
        '''method to retrieve the pipeline of a specific sobject.  The pipeline
        returned is a dictionary

        @params:
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject

        @keyparams:
        recurse - boolean to control whether to display sub pipeline processes
        related_process- given a process, it shows the input and output processes and contexts

        @return:
        dictionary - just the plain processes or more input and output info if related_process is specified
        '''
        from pyasm.biz import Pipeline

        # get the sobject
        from pyasm.search import SearchKey
        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        pipeline = Pipeline.get_by_sobject(sobject)
        if not pipeline:
            return {}

        data = {}
        if related_process:
            input_processes = pipeline.get_input_processes(related_process)
            input_processes = [x.get_name() for x in input_processes]
            data['input_processes'] = input_processes
            output_processes = pipeline.get_output_processes(related_process)
            output_processes = [x.get_name() for x in output_processes]
            data['output_processes'] = output_processes

            input_contexts = pipeline.get_input_contexts(related_process)
            data['input_contexts'] = input_contexts
            output_contexts = pipeline.get_output_contexts(related_process)
            data['output_contexts'] = output_contexts
            return data
        else:
            process_names = pipeline.get_process_names(recurse=recurse)
            data['processes'] = process_names

        return data

    def call_trigger(self, ticket, search_key, event, input={}, process=None):
        '''Calls a trigger with input package

        @params
        ticket - authentication ticket
        search_key - the sobject that contains the trigger
        event - name of event
        input - input data to send to the trigger
        '''
        from pyasm.command import Trigger
        sobjects = [self._sobject(key) for key in (search_key if isinstance(search_key, list) else [search_key])]

        # make sure input is never None
        if input is None:
            input = {}

        count = 0
        for sobject in sobjects:
            triggers = Trigger.call(sobject, event, input, process)
            count += len(triggers)

        return count

    def call_pipeline_event(self, ticket, search_key, process, event, data={}):
        '''Call an even in a process in a pipeline

        @params
        ticket - authentication ticket
        search_key - the sobject that contains the trigger
        process - the process node of the workflow of the sobject
        event - the event to be set
        data - dictionary data that needs to be sent to the process
        '''
        from pyasm.biz import Pipeline
        from pyasm.command import Trigger, Workflow
        from pyasm.command.workflow import _check_workflow
        from pyasm.common import Container

        sobjects = [self._sobject(key) for key in (search_key if isinstance(search_key, list) else [search_key])]

        if event not in ('pending', 'action', 'complete', 'approved', 'not_required', 'reject', 'revise', 'error', 'custom'):
            raise UnsupportedContract('Workflow event is not migrated: %s' % event)
        event = 'process|%s' % event
        data = dict(data or {})
        requested_pipeline = None
        if '::' in process:
            requested_pipeline, process = process.split('::', 1)
        inputs = []
        for sobject in sobjects:
            pipeline_code = requested_pipeline or sobject.get_value("pipeline_code")
            pipeline = Pipeline.get_by_code(pipeline_code)

            input = {
                'pipeline': pipeline,
                'sobject': sobject,
                'process': process,
                'data': data
            }

            if pipeline is None or pipeline.get_process(process) is None:
                raise LookupError('Pipeline process does not exist')
            _check_workflow(input)
            inputs.append(input)
        Workflow().init(quiet=True)
        caller = Container.get_seq('Command:executing')[-1]
        for input in inputs:
            Trigger.call(caller, event, input)

    def get_pipeline_status(self, ticket, search_key, process):
        '''Get the status of a process in a workflow.

        @params
        ticket - authentication ticket
        search_key - the sobject that contains the trigger
        process - the process node of the workflow of the sobject
        '''

        key = "%s|%s|status" % (search_key, process)
        message = self.get_message(ticket, key)
        return message.get("message")

    def add_dependency(self, ticket, snapshot_code, file_path, type='ref', tag='main'):
        '''method to append a dependency reference to an existing checkin.
        The snapshot that this is attached will be auto-discovered

        @params
        ticket - authentication ticket
        snapshot_code - the unique code identifier of a snapshot
        file_path - the path of the dependent file
        type - type of dependency.  Values include 'ref' and 'input_ref'
            ref = hierarchical reference:   ie A contains B
            input_ref - input reference:    ie: A was used to create B
        tag - a tagged keyword can be added to a dependency to categorize
            the different dependencies that exist in a snapshot

        @return
        the resulting snapshot
        '''
        from pyasm.biz import Snapshot
        from pyasm.checkin import SnapshotBuilder
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        if snapshot_code.startswith("sthpw/snapshot?"):
            snapshot = self._sobject(snapshot_code)
        else:
            snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError("Snapshot with code [%s] does not exist" % \
                snapshot_code)

        xml = snapshot.get_xml_value("snapshot")
        builder = SnapshotBuilder(xml)
        builder.add_ref_by_file_path(file_path, type=type, tag=tag)
        snapshot.set_value("snapshot", builder.to_string() )
        snapshot.commit()

        return self._record(snapshot)

    def add_dependency_by_code(self, ticket, to_snapshot_code, from_snapshot_code, type='ref', tag='main'):
        '''method to append a dependency reference to an existing checkin
        The snapshot that this is attached will be auto-discovered

        @params
        ticket - authentication ticket
        to_snapshot_code: the snapshot code which the dependency will be
            connected to
        from_snapshot_code: the snapshot code which the dependency will be
            connected from
        type - type of dependency.  Values include 'ref' and 'input_ref'
            ref = hierarchical reference:   ie A contains B
            input_ref - input reference:    ie: A was used to create B
        tag - a tagged keyword can be added to a dependency to categorize
            the different dependencies that exist in a snapshot

        @return
        the resulting snapshot
        '''
        from pyasm.biz import Snapshot
        from pyasm.checkin import SnapshotBuilder
        if isinstance(to_snapshot_code, dict):
            to_snapshot_code = to_snapshot_code.get('code')
        if isinstance(from_snapshot_code, dict):
            from_snapshot_code = from_snapshot_code.get('code')

        snapshot = Snapshot.get_by_code(to_snapshot_code)
        if not snapshot:
            raise LookupError("Snapshot with code [%s] does not exist" % \
                to_snapshot_code)

        xml = snapshot.get_xml_value("snapshot")
        builder = SnapshotBuilder(xml)
        builder.add_ref_by_snapshot_code(from_snapshot_code, type=type, tag=tag)
        snapshot.set_value("snapshot", builder.to_string() )
        snapshot.commit()

        return self._record(snapshot)

    def lock_sobject(self, ticket, search_key, context):
        '''locks the context for checking in and out
        '''
        from pyasm.biz import Snapshot
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        Snapshot.lock(sobject, context)
        return True

    def unlock_sobject(self, ticket, search_key, context):
        '''unlocks the context for checking in and out
        '''
        from pyasm.biz import Snapshot
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)


        Snapshot.unlock(sobject, context)
        return True

    def get_snapshot(self, ticket, search_key, context="publish", version='-1', revision=None, level_key=None, include_paths=False, include_full_xml=False, include_paths_dict=False, include_files=False, include_web_paths_dict=False, versionless=False, process=None):
        '''method to retrieve snapshots

        @params
        ticket - authentication ticket
        search_key - unique identifier of sobject whose snapshot we are
                looking for
        process - the process of the snapshot
        context - the context of the snapshot
        include_paths - flag to specify whether to include a __paths__ property
            containing a list of all paths in the dependent snapshots
        include_paths_dict - flag to specify whether to include a
            __paths_dict__ property containing a dict of all paths in the
            returned snapshots
        include_web_paths_dict - flag to specify whether to include a
            __web_paths_dict__ property containing a dict of all web paths in
            the returned snapshots
        include_full_xml - flag to return the full xml definition of a snapshot
        include_files - includes all of the file objects referenced in the
            snapshots


        @return
        the resulting snapshot
        '''
        from pyasm.biz import Snapshot

        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        # if the sobject is a snapshot, then get the parent and use it as a base
        if sobject.get_base_search_type() == "sthpw/snapshot":
            sobject = sobject.get_parent()

        search_type = sobject.get_search_type()
        search_id = sobject.get_id()
        search_code = sobject.get_value("code", no_exception=True)
        search_combo = search_code
        if not search_code:
            search_combo = search_id

        # get the level object
        if level_key:
            level = self._sobject(level_key)
            if not level:
                raise LookupError("Level SObject with key [%s] does not exist" % level_key)
            level_type = level.get_search_type()
            level_id = level.get_id()
        else:
            level_type = None
            level_id = None

        # if a process is given the context is overridden
        if process:
            context = None

        if not versionless:
            snapshot = Snapshot.get_snapshot(search_type, search_combo, context=context, version=version, revision=revision, level_type=level_type, level_id=level_id, process=process)

        else:
            if version in (-1, '-1', 'latest'):
                versionless_mode = 'latest'
            else:
                versionless_mode = 'current'
            snapshot = Snapshot._get_versionless(search_type, search_combo, context=context, mode=versionless_mode, create=False, process=process,
                level_type=level_type, level_id=level_id)


        if not snapshot:
            return {}

        sobject_dict = self._record(snapshot)

        # preprocess and get all file objects
        if include_files:
            all_files = Snapshot.get_files_dict_by_snapshots([snapshot])


        # include a paths attribute
        if include_paths:
            paths = snapshot.get_all_client_lib_paths()
            sobject_dict['__paths__'] = paths
        # include a full xml attribute
        if include_full_xml:
            full_snapshot_xml = snapshot.get_full_snapshot_xml()
            sobject_dict['__full_snapshot_xml__'] = full_snapshot_xml

        if include_paths_dict:
            paths = snapshot.get_all_client_lib_paths_dict()
            sobject_dict['__paths_dict__'] = paths

        if include_web_paths_dict:
            paths = snapshot.get_all_web_paths_dict()
            sobject_dict['__web_paths_dict__'] = paths


        if include_files:
            snapshot_code = snapshot.get_code()
            file_list = all_files.get(snapshot_code, [])
            file_dict_list = []
            for file in file_list:
                file_dict = self._record(file)
                file_dict_list.append(file_dict)
            sobject_dict['__files__'] = file_dict_list

        return sobject_dict



    def get_paths(self, ticket, search_key, context="publish", version=-1, file_type='main', level_key=None, single=False, versionless=False, process=None, path_types=[]):
        '''method to get paths from an sobject

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject
        @keyparams:
        context - context of the snapshot
        version - version of the snapshot
        level_key - the unique identifier of the level that this
            was checked into
        single - returns a single path for each category instead of a list
            this is useful if it is know that there is only one file in the
            snapshot
        versionless - boolean to return the versionless snapshot, which takes a version of -1 (latest)  or 0 (current)
        path_types - on of web, client, sandbox, relative

        @return
        A dictionary of lists representing various paths.  The paths returned
        are as follows:
        - client_lib_paths: all the paths to the repository relative to the client
        - lib_paths: all the paths to the repository relative to the server
        - sandbox_paths: all of the paths mapped to the sandbox
        - web: all of the paths relative to the http server

        '''

        from pyasm.biz import Snapshot
        sobjects = [self._sobject(search_key[0] if isinstance(search_key, list) else search_key)]
        sobject = sobjects[0]

        search_type = sobject.get_search_type()
        search_id = sobject.get_code() or sobject.get_id()
        search_key = SearchKey.get_by_sobject(sobject)

        if process:
            context = None

        # get the level object
        if level_key:
            level = self._sobject(level_key)
            if not level:
                raise LookupError("Level SObject with key [%s] does not exist" % level_key)
            level_type = level.get_search_type()
            level_id = level.get_id()
        else:
            level_type = None
            level_id = None

        if not versionless:
            snapshot = Snapshot.get_snapshot(search_type, search_id, context, version, level_type=level_type, level_id=level_id, process=process)
        else:
            if version in (-1, '-1', 'latest'):
                versionless_mode = 'latest'
            else:
                versionless_mode = 'current'
            snapshot = Snapshot._get_versionless(search_type, search_id, context, mode=versionless_mode, create=False, process=process,
                level_type=level_type, level_id=level_id)
        if not snapshot:
            # This is probaby too strict
            #raise LookupError("Snapshot for [%s] with context [%s], version [%s] does not exist" % (search_key, context, version))
            paths = {}
            return paths


        paths = {}
        if file_type == "*":
            client_lib_paths = snapshot.get_all_client_lib_paths()
            sandbox_paths = snapshot.get_all_sandbox_paths()
            web_paths = snapshot.get_all_remote_web_paths()
            lib_paths = snapshot.get_all_lib_paths()

            if single:
                paths['client_lib_path'] = client_lib_paths[0]
                paths['sandbox_path'] = sandbox_paths[0]
                paths['web_path'] = web_paths[0]
                paths['lib_path'] = lib_paths[0]
            else:
                paths['client_lib_paths'] = client_lib_paths
                paths['sandbox_paths'] = sandbox_paths
                paths['web_paths'] = web_paths
                paths['lib_paths'] = lib_paths


        else:
            if "client" in path_types or not path_types:
                client_lib_path = snapshot.get_client_lib_path_by_type(file_type)
                if not client_lib_path:
                    raise LookupError("File of type [%s] does not exist in snapshot [%s]" % (file_type, snapshot.get_code()) )
                if single:
                    paths['client_lib_path'] = client_lib_path
                else:
                    paths['client_lib_paths'] = [client_lib_path]

            if "sandbox" in path_types or not path_types:
                sandbox_path = snapshot.get_sandbox_path_by_type(file_type)
                if single:
                    paths['sandbox_path'] = sandbox_path
                else:
                    paths['sandbox_paths'] = [sandbox_path]


            if "web" in path_types or not path_types:
                web_path = snapshot.get_remote_web_path_by_type(file_type)
                if single:
                    paths['web_path'] = web_path
                else:
                    paths['web_paths'] = [web_path]


            if "lib" in path_types or not path_types:
                lib_path = snapshot.get_lib_path_by_type(file_type)
                if single:
                    paths['lib_path'] = lib_path
                else:
                    paths['lib_paths'] = [lib_path]

            if "relative" in path_types or not path_types:
                relative_path = snapshot.get_web_path_by_type(file_type)
                if single:
                    paths['relative_path'] = relative_path
                else:
                    paths['relative_path'] = [relative_path]


        return paths

    def get_handoff_dir(self, ticket):
        '''simple methods that returns a temporary path that files can be
        copied to

        @params
        ticket - authentication ticket

        @return
        the directory to copy a file to handoff to Tactic without having to
        go through http protocol

        '''
        #web = WebContainer.get_web()
        #return web.get_client_handoff_dir(ticket)
        if isinstance(ticket, dict):
            ticket = ticket.get("ticket")
        env = Environment

        if self.protocol == 'local':
            return env.get_server_handoff_dir(ticket)
        else:
            return env.get_client_handoff_dir(ticket)

    def get_base_dirs(self, ticket):
        '''get all of the base directories defined on the server.'''

        from pyasm.common import Config
        from pyasm.common.config import PATH_SETTINGS, normalize_config_path
        from ast import literal_eval
        data = Config.get_section_values("checkin")
        for key, value in data.items():
            if value.strip().startswith('{'):

                try:
                    sub_value = literal_eval(value.strip())
                    value = sub_value
                    data[key] = value
                except:
                    pass
            if ('checkin', key) in PATH_SETTINGS:
                data[key] = normalize_config_path(value)

        return data

    def get_client_dir(self, ticket, snapshot_code, file_type='main', mode='client_repo'):
        '''method that returns the directory segment of a snapshot for a particular
           file type and mode

        @params
        ticket - authentication ticket
        snapshot_code - unique code of a snapshot
        file_type - each file in a snapshot is identified by a file type.
            This parameter specifies which file type to return.  Defaults to 'main'
        mode - Forces the type of folder path returned to use the value from the
            appropriate tactic_<SERVER_OS>-conf.xml configuration file.
            Values include 'lib', 'web', 'local_repo', 'sandbox', 'client_repo', 'relative'
            lib = the NFS asset directory from the server point of view
            web = the http asset directory from the client point of view
            local_repo = the local sync of the TACTIC repository
            sandbox = the local sandbox (work area) designated by TACTIC
            client_repo (default) = the asset directory from the client point of view
            If there is no value for win32_client_repo_dir or linux_client_repo_dir
            in the config, then the value for asset_base_dir will be used instead.
            relative = the relative direcory without any base

        @return
        string - directory segment for a snapshot and file type

        '''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')

        if snapshot_code.find("?") == -1:
            snapshot = Snapshot.get_by_code(snapshot_code)
        else:
            snapshot = self._sobject(snapshot_code)

        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)
        assert mode in ['lib', 'client_repo', 'sandbox', 'local_repo', 'web', 'relative']
        dir = ''
        if mode == 'lib':
            dir = snapshot.get_lib_dir(file_type=file_type)
        elif mode == 'client_repo':
            dir = snapshot.get_client_lib_dir(file_type=file_type)
        elif mode == 'sandbox':
            dir = snapshot.get_sandbox_dir(file_type=file_type)
        elif mode == 'local_repo':
            dir = snapshot.get_local_repo_dir(file_type=file_type)
        elif mode == 'web':
            dir = snapshot.get_web_dir(file_type=file_type)
        elif mode == 'relative':
            dir = snapshot.get_relative_dir(file_type=file_type)

        return dir

    def get_path_from_snapshot(self, ticket, snapshot_code, file_type='main', mode='client_repo'):
        '''method that returns the checked in path of a file

        @params
        ticket - authentication ticket
        snapshot_code - unique code or search_key of a snapshot
        file_type - each file in a snapshot is identified by a file type.
            This parameter specifies which type.  Defaults to 'main'
        mode - Forces the type of folder path returned to use the value from the
            appropriate tactic_<SERVER_OS>-conf.xml configuration file.
            Values include 'lib', 'web', 'local_repo', 'sandbox', 'client_repo', 'relative'
            lib = the NFS asset directory from the server point of view
            web = the http asset directory from the client point of view
            local_repo = the local sync of the TACTIC repository
            sandbox = the local sandbox (work area) designated by TACTIC
            client_repo (default) = the asset directory from the client point of view
            If there is no value for win32_client_repo_dir or linux_client_repo_dir
            in the config, then the value for asset_base_dir will be used instead.
            relative = the relative direcory without any base

        @return
        string - the directory to copy a file to handoff to Tactic without having to
        go through http protocol

        '''

        if not snapshot_code:
            return ''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')

        if snapshot_code.find("?") == -1:
            snapshot = Snapshot.get_by_code(snapshot_code)
        else:
            snapshot = self._sobject(snapshot_code)
        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        assert mode in ['lib', 'client_repo', 'sandbox', 'local_repo', 'web', 'relative']
        dir = ''
        if mode == 'lib':
            dir = snapshot.get_lib_dir(file_type=file_type)
        elif mode == 'client_repo':
            dir = snapshot.get_client_lib_dir(file_type=file_type)
        elif mode == 'sandbox':
            dir = snapshot.get_sandbox_dir(file_type=file_type)
        elif mode == 'local_repo':
            dir = snapshot.get_local_repo_dir(file_type=file_type)
        elif mode == 'web':
            dir = snapshot.get_web_dir(file_type=file_type)
        elif mode == 'relative':
            dir = snapshot.get_relative_dir(file_type=file_type)

        filename = snapshot.get_file_name_by_type(file_type)
        if filename:
            path = "%s/%s" % (dir, filename)
        else:
            path = ""
        return path

    def get_expanded_paths_from_snapshot(self, ticket, snapshot_code, file_type='main'):
        '''method that returns the expanded path of a snapshot (used for
        ranges of files

        @params
        ticket - authentication ticket
        snapshot_code - unique code of a snapshot
        file_type - each file in a snapshot is identified by a file type.
            This parameter specifies which type.  Defaults to 'main'


        @return
        the directory to copy a file to handoff to Tactic without having to
        go through http protocol

        '''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        client_lib_dir = snapshot.get_client_lib_dir(file_type=file_type)

        file_names = snapshot.get_expanded_file_names(file_type)
        paths = []
        for file_name in file_names:
            path = "%s/%s" % (client_lib_dir, file_name)
            paths.append(path)

        return paths

    def get_all_paths_from_snapshot(self, ticket, snapshot_code, mode='client_repo', expand_paths=False, filename_mode='',file_types=[]):
        '''method that returns all the files in a snapshot

        @params
        ticket - authentication ticket
        snapshot_code - unique code of a snapshot

        @return
        the directory to copy a file to handoff to Tactic without having to
        go through http protocol

        '''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')

        if snapshot_code.find("?") == -1:
            snapshot = Snapshot.get_by_code(snapshot_code)
        else:
            snapshot = self._sobject(snapshot_code)

        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        if file_types:
            paths = []
            for file_type in file_types:
                paths.extend(snapshot.get_paths_by_type(file_type, mode=mode, filename_mode=filename_mode, expand_paths=expand_paths) or [])
        else:
            paths = snapshot.get_all_lib_paths(expand_paths=expand_paths, mode=mode, filename_mode=filename_mode)

        return paths

    def get_dependencies(self, ticket, snapshot_code, mode='explicit', tag='main', include_paths=False, include_paths_dict=False, include_files=False, repo_mode='client_repo', show_retired=False):
        '''method that returns of the dependent snapshots of a certain tag

        @params
        ticket - authentication ticket
        snapshot_code - unique code of a snapshot
        mode - explict (get version as defined in snapshot)
             - latest
             - current
        tag - retrieve only dependencies that have this named tag
        include_paths - flag to specify whether to include a __paths__ property
            containing a list of all paths in the dependent snapshots
        include_paths_dict - flag to specify whether to include a
            __paths_dict__ property containing a dict of all paths in the
            dependent snapshots
        include_files - includes all of the file objects referenced in the
            snapshots
        repo_mode - client_repo, lib, web,...
        show_retired - show the retired results as well if applicable


        @return
        a list of snapshots

        '''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        results = snapshot.get_ref_snapshots(name='tag', value=tag, mode=mode, show_retired=show_retired)
        snapshots = []

        # preprocess and get all file objects
        if include_files or include_paths or include_paths_dict:
            all_files = Snapshot.get_files_dict_by_snapshots(results)


        for result in results:
            snapshot = self._record(result)

            if include_paths:
                paths = result.get_all_lib_paths(mode=repo_mode)
                snapshot['__paths__'] = paths

            if include_paths_dict:
                paths = result.get_all_paths_dict(mode=repo_mode)
                snapshot['__paths_dict__'] = paths

            if include_files:
                snapshot_code = snapshot.get('code')
                file_list = all_files.get(snapshot_code)
                file_dict_list = []
                if file_list:
                    for file in file_list:
                        file_dict = self._record(file)
                        file_dict_list.append(file_dict)
                snapshot['__files__'] = file_dict_list


            snapshots.append(snapshot)
        return snapshots

    def get_all_dependencies(self, ticket, snapshot_code, mode='explicit', type='ref', include_paths=False, include_paths_dict=False, include_files=False, repo_mode='client_repo', show_retired=False):
        '''method that returns of the dependent snapshots for a given
        snapshot

        @params
        ticket - authentication ticket
        snapshot_code - unique code of a snapshot
        mode - explict (get version as defined in snapshot)
             - latest
             - current
        type - one of ref or input_ref
        include_paths - flag to specify whether to include a __paths__ property
            containing all of the paths in the dependent snapshots
        include_paths_dict - flag to specify whether to include a
            __paths_dict__ property containing a dict of all paths in the
            dependent snapshots
        include_files - includes all of the file objects referenced in the
            snapshots
        repo_mode - client_repo, lib, web,...
        show_retired - show the retired results as well if applicable

        @return
        a list of snapshots

        '''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')

        if snapshot_code.find("?") == -1:
            snapshot = Snapshot.get_by_code(snapshot_code)
        else:
            snapshot = self._sobject(snapshot_code)

        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        results = snapshot.get_all_ref_snapshots(mode=mode, type=type, show_retired=show_retired)
        snapshots = []
        all_files = (
            Snapshot.get_files_dict_by_snapshots(results)
            if (include_files or include_paths or include_paths_dict)
            else {}
        )

        for result in results:
            snapshot = self._record(result)

            if include_paths:
                paths = result.get_all_lib_paths(mode=repo_mode)
                snapshot['__paths__'] = paths

            if include_paths_dict:
                paths = result.get_all_paths_dict(mode=repo_mode)
                snapshot['__paths_dict__'] = paths


            snapshots.append(snapshot)


        # preprocess and get all file objects
        if include_files:
            for idx, result in enumerate(results):
                snapshot = snapshots[idx]

                snapshot_code = result.get_code()
                file_list = all_files.get(snapshot_code)
                file_dict_list = []
                # empty snapshot won't have file_list
                if file_list:
                    for file in file_list:
                        file_dict = self._record(file)
                        file_dict_list.append(file_dict)
                snapshot['__files__'] = file_dict_list

        return snapshots

    def group_checkin(self, ticket, search_key, context, file_path, file_range_val, snapshot_type='sequence', description="", file_type='main', metadata={}, mode=None, is_revision=False, info={}, version=None, process=None):
        '''checkin a range of files

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject
        context - the context of the checkin
        file_path - expression for file range: ./blah.####.jpg
        file_range - string describing range of frames in the from '1-5/1'
        snapshot_type - the snapshot type of the checkin
        description - a descriptive comment that pertains to this checkin
        file_type - the type of file this is checked in as. Default = 'main'
        metadata - a dictionary of values that will be stored as metadata
            on the snapshot
        mode - determines whether the files passed in should be preallocate, copied, move
            or uploaded.  By default, this is a manual process (for backwards
            compatibility)
        metadata - add metadata to snapshot
        is_revision - flag to set this as a revision instead of a version
        info - dictionary for ApiClientCmd
        version - explicitly set a version
        process - explicitly set a process


        @return
        snapshot dictionary
        '''

        from pyasm.biz import FileGroup, FileRange
        from pyasm.checkin import FileGroupCheckin
        from pyasm.search import FileUndo
        from pathlib import Path
        if not isinstance(metadata, dict):
            raise ValueError('Group metadata must be a dictionary')
        if mode not in (None, '', 'copy', 'move', 'create', 'upload', 'uploaded', 'inplace'):
            raise ValueError('Unknown group check-in mode')
        info = dict(info)
        if not file_range_val:
            # try to extract from paths
            file_path, file_range_val = FileGroup.extract_template_and_range(file_path)

        file_range = FileRange.get(file_range_val)


        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        # get the handoff dir and remap
        base_dir = Environment.get_upload_dir()

        if mode == 'inplace':
            base_dir = os.path.dirname(file_path[0] if isinstance(file_path, list) else file_path)

        elif mode in ['upload','uploaded']:
            base_dir = Environment.get_upload_dir()
        else:
            base_dir = Environment.get_server_handoff_dir()


        if not isinstance(file_path, list):
            file_path = file_path.replace("\\", "/")
            filename = os.path.basename(file_path)
            if mode != "inplace":
                upload_file_name(filename)
            file_paths = ["%s/%s" % (base_dir, filename)]
        else:
            file_paths = [x.replace("\\", "/") for x in file_path]


        # if file type is not specified, use file_type
        if mode != 'inplace':
            check_ticket_paths(file_paths, base_dir, file_range)
        if not file_type:
            file_type = "main"


        file_types = []
        for file_path in file_paths:
            file_types.append(file_type)


        if not description:
            if file_range:
                description = 'File Group Publish [%s] files' % float(file_range.get_num_frames())
            else:
                description = 'File Group Publish [%s] files' % len(file_paths)

        checkin = FileGroupCheckin(sobject, file_paths, file_types,\
            file_range, context=context, snapshot_type=snapshot_type, \
            description=description, is_revision=is_revision, mode='create' if mode in ('upload', 'uploaded') else mode, \
            version=version, process=process)

        checkin.execute()

        # cleanup
        expanded_paths = checkin.get_expanded_paths()
        for path in expanded_paths:
            if mode != 'inplace' and os.path.exists(path):
                FileUndo.remove(path)

        # get values from snapshot
        snapshot = checkin.get_snapshot()


        # add metadata to the snapshot
        if metadata:
            snapshot.add_metadata(metadata)
            snapshot.commit()

        from pyasm.common import Container
        command = Container.get_seq('Command:executing')[-1]
        command.sobjects.append(sobject)

        info['snapshot'] = snapshot

        command.info.update(info)

        search = Search("sthpw/snapshot")
        columns = search.get_columns()
        result = {}
        for column in columns:
            value = str(snapshot.get_value(column))
            result[column] = value
        result['__search_key__'] = SearchKey.build_by_sobject(snapshot)

        return result

    def add_group(self, ticket, snapshot_code, file_path, file_type, file_range, use_handoff_dir=False, mode=None):
        '''method to add a file range to an already existing snapshot

        @params
        ticket - authentication ticket
        snapshot_code - the unique code identifier of a snapshot
        file_path - path of the file to add to the snapshot
        file_type - type of the file to be added.
        file_range - range of files in the form of "start-end/by"
        use_handoff_dir - determines whether to get the files from the handoff
            directory
        mode - one of 'copy', move', 'preallocate', 'inplace'

        @return
        the resulting snapshot
        '''
        from pyasm.biz import Snapshot, FileRange
        from pyasm.checkin import FileGroupAppendCheckin
        file_range = FileRange.get(file_range)

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError("Snapshot with code [%s] does not exist" % \
                snapshot_code)

        if mode in ("upload", None, ""):
            mode = "create"
        file_path = file_path.replace("\\", "/")
        filename = os.path.basename(file_path)
        #filename = File.get_filesystem_name(filename)

        if mode not in ['move', 'copy', 'create', 'preallocate', 'upload', 'inplace']:
            raise ValueError('Unknown group append mode')
        if mode == 'preallocate':
            keep_file_name = True
            # create a virtual file object for dir naming

            #lib_dir = snapshot.get_lib_dir(file_type=file_type, file_object=file_object)
            #upload_path = "%s/%s" % (lib_dir, filename)
            upload_path = file_path

        elif mode == 'inplace':
            upload_path = os.path.dirname(file_path) + '/' + filename
            keep_file_name = True

        else:
            keep_file_name = False

            dir = Environment.get_upload_dir()
            if use_handoff_dir:
                dir = Environment.get_server_handoff_dir()
            else:
                dir = Environment.get_upload_dir()

            filename = upload_file_name(filename)
            upload_path = "%s/%s" % (dir, filename)
            check_ticket_paths([upload_path], dir, file_range)



        checkin = FileGroupAppendCheckin(snapshot_code, [upload_path], [file_type], file_range, \
                keep_file_name=keep_file_name, mode=mode)
        checkin.execute()
        snapshot = checkin.get_snapshot()
        return self._record(snapshot)

    def query_snapshots(self, ticket, filters=None, columns=None, order_bys=[], show_retired=False, limit=None, offset=None, single=False, include_paths=False, include_full_xml=False, include_paths_dict=False, include_parent=False, include_files=False, include_web_paths_dict=False):
        '''thin wrapper around query, but is specific to querying snapshots
        with some useful included flags that are specific to snapshots

        @params
        ticket - authentication ticket
        filters - (optional) an array of filters to alter the search
        columns - (optional) an array of columns whose values should be
                    retrieved
        order_bys - (optional) an array of order_by to alter the search
        show_retired - (optional) - sets whether retired sobjects are also
                    returned
        limit - sets the maximum number of results returned
        single - returns a single sobject that is not wrapped up in an array
        include_paths - flag to specify whether to include a __paths__ property
            containing a list of all paths in the dependent snapshots
        include_paths_dict - flag to specify whether to include a
            __paths_dict__ property containing a dict of all paths in the
            dependent snapshots
        include_web_paths_dict - flag to specify whether to include a
            __web_paths_dict__ property containing a dict of all web paths in
            the returned snapshots

        include_full_xml - flag to return the full xml definition of a snapshot
        include_parent - includes all of the parent attributes in a __parent__ dictionary
        include_files - includes all of the file objects referenced in the
            snapshots

        @return
        list of snapshots
        '''
        from pyasm.biz import Snapshot
        search_type = "sthpw/snapshot"
        search = self._search(search_type)
        with self._expression_access():
            search.add_op_filters(filters or [])
        search.set_show_retired(show_retired)
        for order in [order_bys] if isinstance(order_bys, str) else order_bys or []:
            search.add_order_by(order)
        if limit:
            search.set_limit(limit)
        if offset:
            search.set_offset(offset)
        snapshots = search.get_sobjects()
        if single:
            snapshots = snapshots[:1]
        parents = {}
        if include_parent:
            parent_by_ref = {}
            for snapshot in snapshots:
                ref = (snapshot.get_value('search_type'), snapshot.get_value('search_code'), snapshot.get_value('search_id'))
                if ref not in parent_by_ref:
                    parent_by_ref[ref] = snapshot.get_parent()
                parents[snapshot.get_search_key()] = parent_by_ref[ref]
        if include_files or include_paths or include_paths_dict or include_web_paths_dict or include_full_xml:
            all_files = Snapshot.get_files_dict_by_snapshots(snapshots)

        results = []
        for snapshot in snapshots:
            snapshot_dict = self._record(snapshot, columns=columns)
            # include a paths attribute
            if include_paths:
                paths = snapshot.get_all_client_lib_paths()
                snapshot_dict['__paths__'] = paths

            # include a full xml attribute
            if include_full_xml:
                full_snapshot_xml = snapshot.get_full_snapshot_xml()
                snapshot_dict['__full_snapshot_xml__'] = full_snapshot_xml

            if include_paths_dict:
                paths = snapshot.get_all_client_lib_paths_dict()
                snapshot_dict['__paths_dict__'] = paths

            if include_web_paths_dict:
                paths = snapshot.get_all_web_paths_dict()
                snapshot_dict['__web_paths_dict__'] = paths

            if include_parent:
                search_key = snapshot_dict.get('__search_key__')
                parent = parents.get(search_key)
                parent_dict = self._record(parent)
                snapshot_dict['__parent__'] = parent_dict

            if include_files:
                snapshot_code = snapshot.get_code()
                file_list = all_files.get(snapshot_code)
                file_dict_list = []
                if file_list:
                    for file in file_list:
                        file_dict = self._record(file)
                        file_dict_list.append(file_dict)
                else:
                    print("Files not found for snapshot [%s]" %snapshot_code)
                snapshot_dict['__files__'] = file_dict_list



            results.append(snapshot_dict)
        return results

    def get_snapshots_by_relative_dir(self, ticket, relative_dir, base_dir_alias=""):
        '''Get all of the snapshots associated with a particular relative
        directory.

        @params
        ticket - authentication ticket
        relative_dir - the relative directory in the server

        @return
        list of snapshots
        '''


        search = Search("sthpw/file")
        if base_dir_alias:
            search.add_filter("base_dir_alias", base_dir_alias)
        search.add_op("begin")
        search.add_filter("relative_dir", "%s/%%" % relative_dir, op="like")
        search.add_filter("relative_dir", "%s" % relative_dir, op="=")
        search.add_op("or")

        search2 = Search("sthpw/snapshot")
        search2.add_relationship_search_filter(search)
        search2.add_filter("is_latest", True)

        sobjects = search2.get_sobjects()
        sobject_dicts = []
        for sobject in sobjects:
            sobject_dict = self._record(sobject)
            sobject_dicts.append(sobject_dict)
        return sobject_dicts

    def set_current_snapshot(self, ticket, snapshot_code):
        '''sets this snapshot as a "current" snapshot

        @params
        ticket - authentication ticket
        snapshot_code - unique code of snapshot

        @return
        the resulting snapshot xml
        '''

        from pyasm.biz import Snapshot
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        # let SnapshotisLatestTrigger handle the rest
        snapshot.set_current()
        #snapshot.set_current(update_versionless=False)
        return self._record(snapshot)

    def get_preallocated_path(self, ticket, snapshot_code, file_type='main', file_name='', mkdirs=True, protocol='client_repo', ext='', checkin_type='strict'):
        '''Gets the preallocated path for this snapshot.  It not assumed that
        this checkin actually exists in the repository and will create virtual
        entities to simulate a checkin.  This method can be used to determine
        where a checkin will go.

        @params
        ticket - authentication ticket
        snapshot_code - the code of a preallocated snapshot.  This can be
            created by get_snapshot()
        file_type - the type of file that will be checked in.  Some naming
            conventions make use of this information to separate directories
            for different file types
        file_name - the desired file name of the preallocation.  This information
            may be ignored by the naming convention or it may use this as a
            base for the final file name
        mkdir - an option which determines whether the directory of the
            preallocation should be created
        protocol - It's either client_repo or None. It determines whether the
            path is from a client or server perspective
        ext - force the extension of the file name returned
        checkin_type - strict, auto , or '' can be used.. A naming entry in the naming, if found,  will be used to determine the checkin type

        @return
        the path where () expects the file to be checked into
        '''

        from pyasm.biz import Snapshot

        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)

        if not snapshot:
            raise LookupError( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        parent = None
        path = snapshot.get_preallocated_path(file_type, file_name, mkdirs, protocol, ext, parent, checkin_type)
        return path


    def get_virtual_snapshot_path(self, ticket, search_key, context, snapshot_type="file", level_key=None, file_type='main', file_name='', mkdirs=False, protocol='client_repo', ext='', checkin_type=''):
        '''creates a virtual snapshot and returns a path that this snapshot
        would generate through the naming conventions''

        @params
        snapshot creation:
        -----------------
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject
        context - the context of the checkin
        snapshot_type - [optional] descibes what kind of a snapshot this is.
            More information about a snapshot type can be found in the
            prod/snapshot_type sobject
        description - [optional] optional description for this checkin
        level_key - the unique identifier of the level that this
            is to be checked into

        path creation:
        --------------
        file_type: the type of file that will be checked in.  Some naming
            conventions make use of this information to separate directories
            for different file types
        file_name: the desired file name of the preallocation.  This information
            may be ignored by the naming convention or it may use this as a
            base for the final file name
        mkdir: an option which determines whether the directory of the
            preallocation should be created
        protocol: It's either client_repo, sandbox, or None. It determines whether the
            path is from a client or server perspective
        ext: force the extension of the file name returned
        checkin_type - strict, auto, '' can be used to predetermine the checkin_type for get_preallocated_path()


        @return
        path as determined by the naming conventions
        '''
        from pyasm.biz import Snapshot

        sobjects = [self._sobject(search_key)]
        sobject = sobjects[0]

        # get the level object
        if level_key:
            level = self._sobject(level_key)
            if not level:
                raise LookupError('Level SObject with key [%s] does not exist' % level_key)
            level_type = level.get_search_type()
            level_id = level.get_id()
        else:
            level_type = None
            level_id = None

        description = "No description"

        # create a virtual snapshot
        snapshot = Snapshot.create(sobject, snapshot_type=snapshot_type, context=context, description=description, level_type=level_type, level_id=level_id, commit=False)

        path = snapshot.get_preallocated_path(file_type, file_name, mkdirs, protocol, ext=ext, checkin_type=checkin_type)
        return path


    def add_file(self, ticket, snapshot_code, file_path, file_type='main', use_handoff_dir=False, mode=None, create_icon=False, dir_naming=None, file_naming=None, checkin_type='strict'):
        '''method to add a file to an already existing snapshot

        @param:
        ticket - authentication ticket
        snapshot_code - the unique code identifier of a snapshot
        file_path - path of the file to add to the snapshot
        file_type - type of the file to be added.
        dir_naming - explicitly set a dir_naming expression to use
        file_naming - explicitly set a file_naming expression to use
        checkin_type - auto or strict which controls whether to auto create versionless or some default file/dir naming

        @return:
        the resulting snapshot
        '''
        from pyasm.biz import Snapshot, IconCreator
        from pyasm.checkin import FileAppendCheckin
        from pyasm.checkin.repo import _check_file_name
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError("Snapshot with code [%s] does not exist" % \
                snapshot_code)

        if mode not in (None, '', 'move', 'copy', 'create', 'preallocate', 'upload', 'uploaded', 'manual', 'inplace'):
            raise ValueError('Unknown append mode: %s' % mode)


        # file_path can be an array of files:
        if not isinstance(file_path, list):
            is_array = False
            file_paths = [file_path]
        else:
            is_array = True
            file_paths = list(file_path)

        if not isinstance(file_type, list):
            file_types = [file_type] * len(file_paths)
        else:
            file_types = list(file_type)

        if not file_paths or len(file_paths) != len(file_types):
            raise ValueError('Each append file requires its file type')
        if not all(isinstance(path, str) for path in file_paths) or not all(isinstance(kind, str) and kind for kind in file_types):
            raise ValueError('Append paths and file types must be strings')

        snapshot_dicts = []

        for i, file_path in enumerate(file_paths):
            # store the passed in path as a source path
            source_paths = []
            source_paths.append(file_path)

            file_type = file_types[i]

            file_path = file_path.replace("\\", "/")
            old_filename = os.path.basename(file_path)
            #filename = File.get_filesystem_name(old_filename)
            filename = old_filename
            _check_file_name(filename)

            if mode == 'preallocate':
                keep_file_name = True
                # create a virtual file object for dir naming
                file_object = SearchType.create("sthpw/file")
                file_object.set_value("file_name", filename)
                file_object.set_value("type", file_type)

                lib_dir = snapshot.get_lib_dir(file_type=file_type, file_object=file_object)
                upload_path = "%s/%s" % (lib_dir, filename)

            elif mode in ('inplace', 'copy', 'move'):
                upload_path = file_path
                keep_file_name = mode == 'inplace'
                if use_handoff_dir and mode in ('copy', 'move'):
                    dir = Environment.get_server_handoff_dir()
                    upload_path = '%s/%s' % (dir, filename)
                    check_ticket_paths([upload_path], dir)
                    source_paths = [upload_path]

            else:
                keep_file_name = False

                dir = Environment.get_server_handoff_dir() if use_handoff_dir else Environment.get_upload_dir()

                upload_path = "%s/%s" % (dir, filename)
                check_ticket_paths([upload_path], dir)

                if filename != old_filename:
                    from pyasm.search import FileUndo
                    FileUndo.move('%s/%s' %(dir, old_filename), upload_path)

            sub_file_paths = [upload_path]
            sub_file_types = [file_type]

            # if this is a file, then try to create an icon
            if create_icon and os.path.isfile(upload_path):
                icon_creator = IconCreator(upload_path)
                # this is icon only mode
                if file_type == 'icon':
                    icon_creator.set_icon_mode()
                    icon_creator.execute()
                    icon_path = icon_creator.get_icon_path()
                    if icon_path:
                        # we keep the source_path as the original file path instead of
                        # of icon_path
                        sub_file_paths = [icon_path]
                        sub_file_types = ['icon']
                else:
                    icon_creator.execute()

                    web_path = icon_creator.get_web_path()
                    icon_path = icon_creator.get_icon_path()
                    for kind, path in (('web', web_path), ('icon', icon_path)):
                        if path:
                            sub_file_paths.append(path)
                            sub_file_types.append(kind)
                            source_paths.append(path if mode in ('copy', 'move') else '')

            #only update versionless for the last file
            do_update_versionless = False
            if i == len(file_paths)-1:
                do_update_versionless = True

            checkin = FileAppendCheckin(snapshot_code, sub_file_paths, sub_file_types, keep_file_name=keep_file_name, mode='create' if mode in ('upload', 'uploaded', 'manual') else mode, source_paths=source_paths, dir_naming=dir_naming, file_naming=file_naming, checkin_type=checkin_type, do_update_versionless=do_update_versionless)
            checkin.execute()
            snapshot = checkin.get_snapshot()

        snapshot_dict = self._record(snapshot)
        return snapshot_dict


    def remove_file(self, ticket, snapshot_code, file_type):
        '''method to remove a file from a snapshot

        @param:
        ticket - authentication ticket
        snapshot_code - the unique code identifier of a snapshot
        file_type - file type to remove

        @return:
        the resulting snapshot
        '''
        from pyasm.biz import Snapshot

        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise LookupError("Snapshot with code [%s] does not exist" % \
                snapshot_code)

        snapshot.remove_file(file_type)

        return self._record(snapshot)

    def simple_checkin(self, ticket, search_key, context, file_path, snapshot_type="file", description="No description",use_handoff_dir=False, file_type='main',is_current=True, level_key=None, metadata={}, mode=None, is_revision=False, info={}, keep_file_name=False, create_icon=True, checkin_cls='pyasm.checkin.FileCheckin', context_index_padding=None, checkin_type="strict", source_path=None, version=None, process=None):

        '''simple methods that checks in a previously uploaded file

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject
        context - the context of the checkin
        file_path - path of the file that was previously uploaded
        snapshot_type - [optional] descibes what kind of a snapshot this is.
            More information about a snapshot type can be found in the
            prod/snapshot_type sobject
        descripton - [optional] optional description for this checkin
        file_type - [optional] optional description for this checkin
        level_key - unique identifier for the level to check this into
        metadata - a dictionary of values that will be stored as metadata
            on the snapshot
        mode - the mode in which files are moved: inplace, upload, copy, move
        is_revision - flag to set this as a revision instead of a version
        info - dictionary for ApiClientCmd
        keep_file_name - keep the original file name
        create_icon - Create an icon by default
        context_index_padding - determines the padding used for context
            indexing: ie: design/0001
        checkin_type - auto or strict which controls whether to auto create versionless
        source_path - explicitly give the source path
        version - force a version for this check-in

        @return
        dictionary representation of the snapshot created for this checkin
        '''

        from pyasm.common import Common
        from pyasm.biz import IconCreator
        from pyasm.search import FileUndo
        FileUndo._check_access()
        if not isinstance(metadata, dict):
            raise ValueError('Check-in metadata must be a dictionary')
        from pyasm.checkin import BaseCheckin
        checkin_class = Common.resolve_class(checkin_cls)
        if not isinstance(checkin_class, type) or not issubclass(checkin_class, BaseCheckin):
            raise TypeError('Check-in class must derive from BaseCheckin')
        if not isinstance(file_path, str) or not isinstance(info, dict):
            raise ValueError('A file path and dictionary command info are required')
        if mode not in (None, '', 'upload', 'uploaded', 'manual', 'create', 'inplace', 'local'):
            raise ValueError('Unsupported simple_checkin mode')
        info = dict(info)
        if isinstance(search_key, dict):
            search_key = search_key.get('__search_key__')

        sobject = self._sobject(search_key)
        if not sobject:
            raise LookupError("SObject for [%s] does not exist" % search_key)

        file_path = file_path.replace("\\", "/")
        # store the source file_path
        if not source_path:
            source_paths = [file_path]
        else:
            source_paths = [source_path]

        old_filename = upload_file_name(file_path)
        #filename = File.get_filesystem_name(old_filename)
        filename = old_filename


        env = Environment
        if mode == 'inplace':
            upload_path = file_path
        else:
            if use_handoff_dir:
                dir = env.get_server_handoff_dir()
            else:
                dir = env.get_upload_dir()
            ticket_dir = dir


            if checkin_type == 'auto' or not checkin_type:
                # In "auto" mode, we can make some assumptions: the file
                # location is based on the context
                parts = context.split("/")
                if len(parts) > 2:
                    subcontext = "/".join( parts[1:-1] )
                    auto_dir = "%s/%s" % (dir, subcontext)
                    check_ticket_paths([auto_dir], ticket_dir, check_contents=False)
                    if os.path.exists(auto_dir):
                        dir = auto_dir



            upload_path = "%s/%s" % (dir, filename)
            check_ticket_paths([upload_path], ticket_dir)
            old_path = '%s/%s' %(dir, old_filename)
            # the upload logic may have already done the conversion
            if filename != old_filename and os.path.exists(old_path):
                FileUndo.move(old_path, '%s/%s' %(dir, filename))

        file_paths = [upload_path]
        file_types = [file_type]

        # if this is a file, then try to create an icon
        if os.path.isfile(upload_path) and create_icon:
            icon_creator = IconCreator(upload_path)
            icon_creator.execute()

            web_path = icon_creator.get_web_path()
            icon_path = icon_creator.get_icon_path()

            # If this is pure icon context, then don't check in icon
            # as the main file.
            if context == 'icon':
                if web_path:
                    FileUndo.copy(web_path, upload_path)
                elif icon_path:
                    FileUndo.copy(icon_path, upload_path)

            # If web file is not generated and icon is, use original as web.
            if icon_path and not web_path:
                base, ext = os.path.splitext(upload_path)
                web_path = "%s_web%s" % (base, ext)
                FileUndo.copy(upload_path, web_path)

            if web_path:
                file_paths.append(web_path)
                file_types.append('web')
                source_paths.append(web_path)

            if icon_path:
                file_paths.append(icon_path)
                file_types.append('icon')
                source_paths.append(icon_path)


        # get the level object
        if level_key:
            level = self._sobject(level_key)
            if not level:
                raise LookupError("Level SObject with key [%s] does not exist" % level_key)
            level_type = level.get_search_type()
            level_id = level.get_id()
        else:
            level_type = None
            level_id = None


        checkin_args = [sobject, file_paths]
        checkin_kwargs = {'file_types': file_types, 'context': context,
            'snapshot_type': snapshot_type, 'description': description,
            'is_current': is_current, 'source_paths': source_paths,
            'level_type': level_type, 'level_id': level_id,
            'mode': 'create' if mode in ('upload', 'uploaded', 'manual') else mode, 'is_revision': is_revision,
            'keep_file_name': keep_file_name,
            'context_index_padding': context_index_padding,
            'checkin_type': checkin_type, 'version': version,
            'process': process
        }

        checkin = checkin_class(*checkin_args, **checkin_kwargs)


        checkin.execute()



        # get values from snapshot
        snapshot = checkin.get_snapshot()
        file_sobjs = checkin.get_file_objects()
        file_dicts = []
        for file_sobj in file_sobjs:
            file_dict = self._record(file_sobj)
            file_dicts.append(file_dict)



        # NOTE: this might need to be an argument for FileCheckin?
        if metadata:
            snapshot.add_metadata(metadata, replace=True)
            snapshot.commit()

        from pyasm.common import Container
        commands = Container.get('Command:executing') or []
        command = commands[-1] if commands else None
        if command:
            command.sobjects = [sobject]

        info['snapshot'] = snapshot
        if command:
            command.info.update(info)

        snapshot_dict = self._record(snapshot)
        snapshot_dict['__file_sobjects__'] = file_dicts

        # include paths for all the files that are checked in
        if mode == 'local':
            local_paths = snapshot.get_all_local_repo_paths()
            snapshot_dict['__paths__'] = local_paths

        #print("SQL Commit Count: ", Container.get('Search:sql_commit'))
        return snapshot_dict


    def subscribe(self, ticket, key, category=None):
        '''Allow a user to subscribe to this message key.  All messages
        belonging to the corresponding key will be available to users
        subscribed to it.

        @params
        ticket - authentication ticket
        key - unique key for this message in the message_code column

        @keyparam
        category - value to categorize this message

        @return
        subscription sobject
        '''

        from pyasm.web.api_xmlrpc import ApiException
        from pyasm.security import Sudo
        search = Search("sthpw/subscription")
        search.add_user_filter()
        search.add_filter("message_code", key)
        search.add_filter("project_code", Project.get_project_code())
        subscription  = search.get_sobject()

        if subscription:
            raise ApiException('[%s] has already been subscribed to.'%key)
            # nothing to do ... already subscribed
            #sobject_dict = self._record(subscription)
            #return sobject_dict

        project_code = Project.get_project_code()

        sudo = Sudo()
        try:
            subscription = SearchType.create("sthpw/subscription")
            subscription.set_value("message_code", key)
            subscription.set_value("project_code", project_code)
            subscription.set_user()
            if category:
                subscription.set_value("category", category)
            subscription.commit()
        finally:
            sudo.exit()

        sobject_dict = self._record(subscription)
        return sobject_dict


    def unsubscribe(self, ticket, key):
        '''Allow a user to unsubscribe from this message key.

        @params
        ticket - authentication ticket
        key - unique key for this message in the message_code column

        @return:
        dictionary - the values of the subscription sobject in the
        form name:value pairs
        '''

        from pyasm.web.api_xmlrpc import ApiException
        from pyasm.security import Sudo
        project_code = Project.get_project_code()

        sudo = Sudo()
        try:
            search = Search("sthpw/subscription")
            search.add_user_filter()
            search.add_filter("message_code", key)
            search.add_filter("project_code", project_code)
            subscription  = search.get_sobject()
        finally:
            sudo.exit()

        if not subscription:
            raise ApiException('[%s] is not subscribed to.'%key)
            # nothing to do ... item is not subscribed to

        subscription.delete()

        return self._record(subscription)


    def add_interaction(self, ticket, key, data={}):

        from pyasm.common import jsondumps
        interaction = SearchType.create("sthpw/interaction")
        interaction.set_value("key", key)
        if data:
            interaction.set_value("data", jsondumps(data))

        interaction.set_user()
        project_code = Project.get_project_code()
        interaction.set_value("project_code", project_code)

        interaction.commit()
        sobject_dict = self._record(interaction)
        return sobject_dict


    def get_interaction_count(self, ticket, key):
        interaction = Search("sthpw/interaction")
        interaction.add_filter("key", key)
        return interaction.get_count()


    def set_widget_setting(self, ticket, key, value):
        '''API Function: set_widget_settings(key, value)
        Set widget setting for current user and project

        @param
        key - unique key to identify this setting
        value - value the setting should be set to

        @return
        None
        '''
        from pyasm.web import WidgetSettings
        WidgetSettings.set_value_by_key(key, value)
        return True


    def get_widget_setting(self, ticket, key):
        '''API Function: set_widget_settings(key, value)
        Get widget setting for current user and project

        @param
        key - unique key to identify this setting

        @return
        value of setting
        '''
        from pyasm.web import WidgetSettings
        return WidgetSettings.get_value_by_key(key)


    def get_plugin_dir(self, ticket, plugin_code):
        '''gets the plugin directory from the client perspective'''

        from pyasm.search import SObject
        if isinstance(plugin_code, SObject):
            plugin = plugin_code
            plugin_code = plugin.get("code")
        elif isinstance(plugin_code, dict):
            plugin = plugin_code
            plugin_code = plugin.get("code")
        else:
            search = Search("config/plugin")
            search.add_filter("code", plugin_code)
            plugin = search.get_sobject()
        if not plugin:
            rel_dir = plugin_code
        else:
            rel_dir = plugin.get("rel_dir")

        if plugin_code.startswith("TACTIC"):
            return "/tactic/builtin_plugins/%s" % rel_dir
        else:
            return "/tactic/plugins/%s" % rel_dir


    def update_config(self, ticket, search_type, view, element_names, login=None, deleted_element_names=[]):
        '''update a widget config for a view

        @params:
        search_type: the search type that this config belongs to
        view: the specific view of the search type
        element_names: all of the element names in this view
        '''

        from pyasm.common import Xml, Common
        config_search_type = "config/widget_config"
        search = Search(config_search_type)
        search.add_filter("search_type", search_type)
        search.add_filter("view", view)
        # Personal edits must not select the shared view.
        search.add_filter("login", login)
        config = search.get_sobject()
        if not config:
            config = SearchType.create(config_search_type)
            config.set_value("search_type", search_type )
            config.set_value("view", view )
            if login:
                config.set_value("login", login)

        elif not element_names:
            element_names = config.get_element_names()

        # create a new document
        xml = Xml()
        xml.create_doc("config")
        root = xml.get_root_node()
        view_node = xml.create_element("view", attrs={"name": view}) if config.view_as_attr else xml.create_element(view)
        #root.appendChild(view_node)
        xml.append_child(root, view_node)


        # build a new config
        for element_name in element_names:
            deleted_element_names = Common.get_unique_list(deleted_element_names)
            if element_name in deleted_element_names:
                continue

            # if the old xml has it defined, then keep it
            element = config.get_element_node(element_name)
            if element is not None:
                element = xml.import_node(element, True)
            else:
                # else create a new one
                element = xml.create_element("element")
                xml.set_attribute(element, "name", element_name)

            #view_node.appendChild(element)
            xml.append_child(view_node, element)

        config.set_value("config", xml.to_string())
        config.commit()


        # delete any unwanted items in definition
        config_search_type = "config/widget_config"
        search = Search(config_search_type)
        search.add_filter("search_type", search_type)
        search.add_filter("view", "definition")
        search.add_filter("login", login)
        def_config = search.get_sobject()
        if def_config:
            def_xml = def_config.get_xml()
            deleted_element_names = Common.get_unique_list(deleted_element_names)
            for name in deleted_element_names:
                element = def_config.get_element_node(name)
                if element is not None:
                    # check if it is a folder and delete its view entry also
                    display_handler = def_config.get_display_handler(name)

                    if display_handler == 'SideBarSectionLinkWdg':
                        options = def_config.get_display_options(name)
                        folder_view = options.get('view')
                        search = Search(config_search_type)
                        search.add_filter("search_type", 'SideBarWdg')
                        search.add_filter("view", folder_view)
                        search.add_filter("login", login)
                        folder_config = search.get_sobject()
                        if folder_config:
                            folder_config.delete()
                    #node = element.parentNode.removeChild(element)
                    parent_node = def_xml.get_parent(element)
                    def_xml.remove_child(parent_node, element)


            def_config.commit_config()
        return xml.to_string()


    def add_config_element(self, ticket, search_type, view, name, class_name=None,
           display_options={}, action_class_name=None, action_options={}, element_attrs={},
           login=None, unique=True, auto_unique_name=False, auto_unique_view=False, view_as_attr=False):
        '''Add an element into a config

        @params:
        search_type - the search type that this config belongs to
        view - the specific view of the search type
        name - the name of the element
        class_name - the fully qualified class of the display
        action_class_name - the fully qualified class of the action
        display_options - keyward options in a dictionary to construct the specific display
        action_options - keyward options in a dictionary to construct the specific display
        element_attrs - element attributes in a dictionary
        login - login of the user specific to this view
        auto_unique_name - auto generate a unique element and display view name
        auto_unique_view - auto generate a unique display view name
        unique - a unique display view name is expected
        view_as_attr - view should be read or created as a name attribute
        '''

        from pyasm.common import Xml, Common
        from pyasm.search import WidgetDbConfig
        import re
        assert view
        config_search_type = "config/widget_config"

        search = Search(config_search_type)
        search.add_filter("search_type", search_type)
        search.add_filter("view", view)
        search.add_filter("login", login)

        config = search.get_sobject()

        display_options = display_options.copy()
        configs = _internal_widget_configs(["definition"])

        internal_names = ['search','publish','edit','insert','edit_definition','definition']
        existing_names = []
        for internal_config in configs:
            internal_names.extend(internal_config.get_element_names())
        if config:
            db_element_names = config.get_element_names()
            existing_names.extend(db_element_names)

        from pyasm.common import UserException
        # error on name starting with number
        pat = re.compile(r'^\d+.*')
        if pat.search(name):
            raise UserException('The name [%s] should not start with a number.'%name)

        if not view_as_attr and view.find('@') != -1:
            view_as_attr = True

        # error out on all special chars from name except .
        pat = re.compile(r'[\$\s,#~`\%\*\^\&\(\)\+\=\[\]\[\}\{\;\:\'\"\<\>\?\|\\\!]')
        if pat.search(name):
            raise UserException('The name [%s] contains special characters or spaces.'%name)

        if unique:
            if name in existing_names:
                raise UserException('This view name [%s] has been taken.'%name)
            if name in internal_names:
                raise UserException('This view name [%s] is reserved for internal use.'%name)


        if config and auto_unique_name:
            # remove all special chars from name except .
            pat = re.compile(r'[\$\s,@#~`\%\*\^\&\(\)\+\=\[\]\[\}\{\;\:\'\"\<\>\?\|\\\!]')
            name = pat.sub('', name)

            suffix = Common.randint(0, 100)
            existing_names = config.get_element_names()
            if name in existing_names:
                new_name = '%s%0.3d' %(name, suffix)
                while True:
                    if new_name in existing_names:
                        suffix += 1
                        new_name = '%s%0.3d' %(name, suffix)
                    else:
                        name = new_name
                        break
            # update the view only if it is a folder since the view is derived from the title
            if auto_unique_view:
                tmp_view = display_options.get('view')
                if tmp_view:
                    display_options['view'] = name
        if not config:
            defaults = _internal_widget_configs([view], base_only=True) if view != 'definition' else []
            config = SearchType.create(config_search_type)
            config.set_value("search_type", search_type)
            config.set_value("view", view)
            if login:
                config.set_value("login", login)
            if defaults:
                config.set_value("config", defaults[0].get_value("config"))
            else:
                xml = Xml()
                root = xml.create_doc('config')
                node = xml.create_element('view', attrs={'name': view}) if view_as_attr else xml.create_element(view)
                xml.append_child(root, node)
                config.set_value('config', xml.to_string())
            config._init()
        config.append_display_element(name, cls_name=class_name, options=display_options,
            element_attrs=element_attrs, action_options=action_options, action_cls_name=action_class_name,
            view_as_attr=view_as_attr)

        config.commit_config()
        # this name could be regenerated. so we return it to client
        dict = {'element_name': name}

        return dict


    def clear_upload_dir(self, ticket):
        from pathlib import Path
        from pyasm.search import FileUndo
        FileUndo._check_access()
        root = Path(Environment.get_tmp_dir()) / 'upload'
        upload_dir = Path(Environment._ticket_directory(root, Environment.get_ticket(), create=False))
        if not upload_dir.is_dir():
            return False
        FileUndo.remove(str(upload_dir))
        return True

    def fast_query(self, ticket, search_type, filters=None, limit=None):
        from pyasm.common import Config
        from pyasm.web.api_xmlrpc import ApiException
        from pyasm.security.security import _require_admin
        if Config.get_value('security', 'enable_fast_query') != 'true':
            raise ApiException('Cannot call fast_query() without enabling in TACTIC config file')
        _require_admin()
        # Preserve authentication rather than install the original empty Security.
        result = self.query(ticket, search_type, filters=filters, limit=limit)
        # Source fast_query bypasses the local decorator and retains Python serialization.
        return repr(result) if self.protocol == 'local' else result

    def set_config_definition(self, ticket, search_type, element_name, config_xml="", login=None):
        from pyasm.common import Xml
        if not config_xml:
            xml = Xml()
            element = xml.create_doc('element')
            xml.set_attribute(element, 'name', element_name)
            xml.set_attribute(element, 'title', ' '.join(x.capitalize() for x in element_name.split('_')))
            display = xml.create_element('display')
            xml.append_child(element, display)
            if element_name.startswith('new_folder'):
                xml.set_attribute(display, 'class', 'SideBarSectionLinkWdg')
                xml.append_child(display, xml.create_text_element('view', element_name))
            elif element_name.startswith(('separator', 'new_separator')):
                xml.set_attribute(display, 'class', 'SeparatorWdg')
            else:
                xml.set_attribute(display, 'class', 'LinkWdg')
            config_xml = xml.to_string()
        element = Xml(config_xml).get_root_node()
        if element.tag != 'element' or element.get('name') != element_name:
            raise ValueError('Configuration must contain the requested element')
        search = Search('config/widget_config')
        search.add_filter('search_type', search_type)
        search.add_filter('view', 'definition')
        search.add_filter('login', login)
        config = search.get_sobject()
        if not config:
            config = SearchType.create('config/widget_config')
            config.set_value('search_type', search_type)
            config.set_value('view', 'definition')
            if login:
                config.set_value('login', login)
            config.set_value('config', '<config><definition/></config>')
            config._init()
        config.append_xml_element(element_name, config_xml)
        config.commit_config()
        return True

    def get_config_definition(self, ticket, search_type, view, element_name, personal=False):
        from pyasm.search import WidgetDbConfig
        from pyasm.common import Xml
        configs = []
        login = Environment.get_user_name() if personal else None
        if view == 'children':
            defaults = json.loads((files('tactic_stream') / 'compatibility/widget_defaults.json').read_text(encoding='utf-8'))
            configs.append(WidgetDbConfig(columns={'id': -1, 'view': view, 'config': defaults['children']}))
        elif view == 'definition':
            search = Search('config/widget_config')
            search.add_filter('search_type', search_type)
            search.add_filter('view', view)
            search.add_filter('login', login)
            config = search.get_sobject()
            if config:
                configs.append(config)
            configs.extend(_internal_widget_configs(['definition']))
        else:
            search = Search('config/widget_config')
            search.add_filter('search_type', search_type)
            search.add_filter('view', view)
            search.add_order_by('priority desc')
            config = search.get_sobject()
            if config:
                configs.append(config)
            configs.extend(_internal_widget_configs([view]))
            for user in ([login, None] if personal else [None]):
                search = Search('config/widget_config')
                search.add_filter('search_type', search_type)
                search.add_filter('view', 'definition')
                search.add_filter('login', user)
                config = search.get_sobject()
                if config:
                    configs.append(config)
            configs.extend(_internal_widget_configs(['definition']))
        # Original WidgetConfigView.get_element_node chooses the first complete
        # definition, then falls back to a reference in the first config.
        for config in configs:
            node = config.get_element_node(element_name)
            if node is not None and (len(Xml.get_attributes(node)) > 1 or config.get_xml().get_children(node)):
                return config.get_xml().to_string(node)
        node = configs[0].get_element_node(element_name) if configs else None
        return configs[0].get_xml().to_string(node) if node is not None else ''


    def generate_ticket(self, ticket):
        from pyasm.common import Common
        return Common.generate_random_key()

    def test_speed(self, ticket):
        '''simple test to verify that the xmlrpc connection is working'''
        from pyasm.security.security import _require_admin
        _require_admin()
        search = Search("sthpw/ticket")
        #search.add_limit(10)
        sobjects = search.get_sobjects()
        sobject_dicts = []
        for sobject in sobjects:
            #sobject_dict = self._record(sobject)
            sobject_dict = sobject.get_data()
            sobject_dicts.append(sobject_dict)
        return str(sobject_dicts)

    def test_error(self, ticket):
        '''simple test to verify that the xmlrpc connection is working'''
        big_fat_error

    def checkout(self, ticket, search_key, context, version=-1, file_type='main', level_key=None):
        '''method to checkout a snapshot from the repository.  This method
        does not move files as the check out process is mostly a client side
        operation.

        @params
        ticket - authentication ticket
        search_key - a unique identifier key representing an sobject
        context - context of the snapshot
        version - version of the snapshot
        level_key - the unique identifier of the level that this
            was checked into

        @return
        a list of paths
        '''

        #paths = self.get_paths(self, ticket, search_key, context="publish", version=-1, file_type='main', level_key=None):

        from pyasm.common import Xml
        from pyasm.biz import Snapshot
        from pyasm.command import Trigger
        from pyasm.web.api_xmlrpc import ApiException
        if not context:
            context = 'publish'

        sobject = self._sobject(search_key[0] if isinstance(search_key, list) else search_key)

        from dataclasses import replace
        from pyasm.search.search import _context
        project = sobject.get_project_code()
        if not Environment.get_security().is_admin() and not Environment.get_security().check_access(
                'project', [{'code': '*'}, {'code': project}], 'allow', default='deny'):
            raise SecurityException('Checkout requires access to the parent project')
        # Keep the request identity, transaction and pool while resolving the parent's paths/callbacks.
        token = _context.set(replace(_context.get(), project=project))
        try:
            search_type = sobject.get_search_type()
            search_id = sobject.get_id()
            search_key = SearchKey.get_by_sobject(sobject)
            if level_key:
                level = self._sobject(level_key)
                if not level:
                    raise ApiException('Level SObject with key [%s] does not exist' % level_key)
                level_type = level.get_search_type()
                level_id = level.get_id()
            else:
                level_type = None
                level_id = None

            snapshot = Snapshot.get_snapshot(search_type, search_id, context, version, level_type=level_type, level_id=level_id)
            if not snapshot:
                raise ApiException("Snapshot for [%s] with context [%s] does not exist" % (search_key, context))

            security = Environment.get_security()
            if not security.is_admin():
                xml = snapshot.get_snapshot_xml()
                codes = {Xml.get_attribute(node, 'file_code') for node in xml.get_nodes('snapshot/file')
                         if file_type == '*' or (Xml.get_attribute(node, 'type') or 'main') == file_type}
                files = Search('sthpw/file')
                files.add_filters('code', list(codes))
                files = files.get_sobjects() if codes else []
                if {file.get_code() for file in files} != codes:
                    raise SecurityException('Checkout file references are not visible')
                for obj in [sobject, snapshot, *([level] if level_key else []), *files]:
                    base = obj.get_base_search_type()
                    object_project = obj.get_value('project_code', no_exception=True) or obj.get_project_code()
                    if not security.check_access('project', [{'code': '*'}, {'code': object_project}], 'allow', default='deny'):
                        raise SecurityException('Checkout referenced project access denied')
                    keys = [{'code': base}, {'code': base, 'project': object_project},
                            {'code': '*'}, {'code': '*', 'project': object_project}]
                    if not security.check_access('search_type', keys, 'view', default='deny') or not security.check_access(
                            'sobject', {'project': object_project, 'search_type': base, 'code': obj.get_code()}, 'view'):
                        raise SecurityException('Checkout object access denied')
                    for column in obj.get_data():
                        if not security.check_access('sobject_column',
                                {'project': object_project, 'search_type': base, 'column': column}, 'view'):
                            raise SecurityException('Checkout column access denied')

            is_locked = snapshot.is_locked(sobject, context)
            if is_locked:
                raise ApiException("Snapshot for [%s] with context [%s] is locked" % (search_key, context))

            paths = {}

            if file_type == "*":
                client_lib_paths = snapshot.get_all_client_lib_paths()
                paths['client_lib_paths'] = client_lib_paths

                sandbox_paths = snapshot.get_all_sandbox_paths()
                paths['sandbox_paths'] = sandbox_paths

                web_paths = snapshot.get_all_remote_web_paths()
                paths['web_paths'] = web_paths

            else:
                client_lib_path = snapshot.get_client_lib_path_by_type(file_type)
                if not client_lib_path:
                    raise ApiException("File of type [%s] does not exist in snapshot [%s]" % (file_type, snapshot.get_code()) )

                sandbox_path = snapshot.get_sandbox_path_by_type(file_type)
                web_path = snapshot.get_remote_web_path_by_type(file_type)

                paths['client_lib_paths'] = [client_lib_path]
                paths['sandbox_paths'] = [sandbox_path]
                paths['web_paths'] = [web_path]

            from pyasm.biz import File, FileGroup, FileRange
            nodes = [node for node in snapshot.get_snapshot_xml().get_nodes('snapshot/file')
                     if file_type == '*' or (Xml.get_attribute(node, 'type') or 'main') == file_type]
            if file_type != '*':
                nodes = nodes[:1]
            ranges = []
            files_dict = snapshot._get_files_dict(snapshot.get_snapshot_xml()) if nodes else {}
            for node in nodes:
                code = Xml.get_attribute(node, 'file_code')
                file = files_dict.get(code) or File.get_by_code(code)
                ranges.append(FileRange.get(file.get_file_range())
                              if file and file.get_value('base_type') == 'sequence' else None)
            if any(ranges):
                if any(len(values) != len(nodes) for values in paths.values()):
                    raise ApiException('Checkout sequence paths do not match their File references')
                expanded = {name: [] for name in paths}
                for index, file_range in enumerate(ranges):
                    for name, values in paths.items():
                        expanded[name].extend(FileGroup.expand_paths(values[index], file_range)
                                              if file_range else [values[index]])
                paths = expanded


            # call some triggers
            base_search_type = sobject.get_base_search_type()
            output = {}
            snapshot_dict = self._record(snapshot)
            output['snapshot'] = snapshot_dict
            output['paths'] = paths
            caller = Container.get_seq('Command:executing')[-1]
            Trigger.call(caller, 'checkout', output)
            Trigger.call(caller, 'checkout|%s' % base_search_type, output, project_code=Project.get_project_code())

            return paths
        finally:
            _context.reset(token)

    def get_full_snapshot_xml(self, ticket, snapshot_code):
        '''method to retrieve a full snapshot xml.  This snapshot definition
        contains all the information about a snapshot in xml

        @params
        ticket - authentication ticket
        snapshot_code - unique code of snapshot

        @return
        the resulting snapshot xml
        '''

        from pyasm.biz import Snapshot
        from pyasm.web.api_xmlrpc import ApiException
        if isinstance(snapshot_code, dict):
            snapshot_code = snapshot_code.get('code')
        snapshot = Snapshot.get_by_code(snapshot_code)
        if not snapshot:
            raise ApiException( "Snapshot with code [%s] does not exist" % \
                snapshot_code)

        return snapshot.get_full_snapshot_xml()

    def execute_class_method(self, ticket, class_name, method, kwargs):
        from pyasm.common import Common
        from tactic.command.python_cmd import check_script_execution
        check_script_execution()
        ret_val = Common.create_from_method(class_name, method, kwargs)
        return ret_val

    def add_queue_item(self, ticket, class_name, args={}, queue=None, priority=9999, description=None, message_code=None):
        '''API Function: Add an item to the job queue

        @param
        class_name - Fully qualified command class derived from pyasm.command.Command
        args - Keyword arguments to pass to the command
        priority - NOT USED ... priority of the job
        queue - Named queue which categorizes a job.  Some queue managers only look
                at one type of queue
        description - a description of the job
        message_code - message log code where messages from the job can be added.

        @return
        queue_item

        '''
        from tactic.command import Queue
        queue_item = Queue.add(class_name, args, queue, priority, description, message_code)
        sobject_dict = self._record(queue_item)
        return sobject_dict

    def get_doc_link(self, ticket, alias):

        install_dir = Environment.get_install_dir()
        alias_path = "%s/doc/alias.json" % install_dir
        if os.path.exists(alias_path):
            f = open(alias_path)
            aliases_str = f.read()
            f.close()
        else:
            aliases_str = "{}"

        aliases = json.loads(aliases_str)
        if not os.path.exists(alias_path):
            aliases = json.loads((files('tactic_stream') / 'compatibility/doc_aliases.json').read_text(encoding='utf-8'))
        path = aliases.get(alias)
        if not path:
            return "none_found"
        else:
            return path

    def get_connection_info(self, ticket):
        """Original response fields, using the current native request's connections."""
        from pyasm.common import Container
        from pyasm.security.security import _require_admin
        _require_admin()
        environ = Container.get('Api:environ') or {}
        databases = {}
        for sql in (Container.get('DbContainer::thread_pool') or {}).values():
            if sql.get_connection() is not None:
                name = sql.get_database_name()
                databases[name] = databases.get(name, 0) + 1
        return dict(keys=list(environ), port=environ.get('SERVER_PORT'), global_pool=[],
                    thread_pool=list(databases), num_database_connections=sum(databases.values()),
                    databases=databases)


# Existing native imports retain their name; the implementation uses TACTIC's name.
Api = ApiXMLRPC
