"""Documented server options, read through the native TACTIC Config."""
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from pyasm.common import Config
from pyasm.common.config import PATH_SETTINGS
from pyasm.common.errors import SecurityException


# section, key, label, explanation, fallback, needs restart
SETTINGS = (
    ('services', 'enable', 'Enabled services', 'tactic serves the web interface and API. Its monitored updates process coalesces committed changes for SSE clients. queue runs background commands in a separate monitored process. files runs bulk verification and retention for file projects.', 'tactic', True),
    ('services', 'process_count', 'Web workers', 'Number of web/API worker processes. Workers share a listener unless explicit ports are set; the monitor restarts failed workers.', '3', True),
    ('services', 'thread_count', 'Request threads per worker', 'Maximum simultaneous blocking operations in each web worker.', '50', True),
    ('services', 'check_interval', 'Monitor check interval', 'Seconds between monitor checks and queue polls.', '1', True),
    ('services', 'update_interval', 'Update collection interval', 'Seconds between collection and distribution of committed changes. Lower values reduce latency; higher values combine more changes. Range: 0.1–2 seconds.', '0.5', True),
    ('services', 'worker_timeout', 'Unresponsive worker timeout', 'Seconds without a heartbeat before a worker is restarted. Also limits a running queue command.', '120', True),
    ('services', 'startup_timeout', 'Worker startup timeout', 'Seconds allowed for a new worker to become ready.', '60', True),
    ('services', 'shutdown_timeout', 'Graceful shutdown timeout', 'Seconds allowed for requests to finish when stopping a web worker.', '10', True),
    ('services', 'restart_delay', 'Restart delay', 'Initial delay in seconds before restarting a failed worker; repeated failures increase the delay.', '1', True),
    ('install', 'hostname', 'Listen address', 'Network address to bind. 127.0.0.1 accepts local connections; 0.0.0.0 listens on all IPv4 interfaces.', '127.0.0.1', True),
    ('services', 'start_port', 'First web port', 'Shared web/API listener port unless an explicit worker port list is set.', '8081', True),
    ('services', 'ports', 'Explicit worker ports', 'Pipe-separated ports, for example 8081|8082|8083. Overrides the first port and worker count; Apache must target these ports.', None, True),
    ('install', 'base_url', 'Public base URL', 'Optional public URL for generated links outside an HTTP request. Requests use their actual public origin.', None, False),
    ('database', 'vendor', 'Database engine', 'SQLite needs no database server. PostgreSQL uses a separate server. Changing this setting does not migrate existing data.', 'Sqlite', True),
    ('database', 'sobject_database', 'System database', 'Database holding users, projects, tickets and the system registry. Project databases are managed separately.', 'sthpw', True),
    ('database', 'host', 'Database host', 'PostgreSQL server hostname or address. Not used for SQLite.', None, True),
    ('database', 'server', 'Alternative database host', 'Legacy alternative to database/host; used only when host is empty.', None, True),
    ('database', 'port', 'Database port', 'PostgreSQL port. An empty value uses the database driver default.', None, True),
    ('database', 'user', 'Database user', 'PostgreSQL account used by the backend. Not used for SQLite.', None, True),
    ('database', 'password', 'Database password', 'Secret value. Never returned to the interface.', None, True),
    ('database', 'password_file', 'Database password file', 'A secret file supplying the database password instead of an inline password. Its contents and path are not returned.', None, True),
    ('checkin', 'asset_base_dir', 'Server repository root', 'Directory containing checked-in files. May map repository aliases to directories; relative paths start at the data directory.', 'assets', True),
    ('checkin', 'web_base_dir', 'Repository web URL', 'Public path or external URL used by clients to download repository files; aliases must match repository roots.', None, True),
    ('checkin', 'base_dir_alias', 'Additional repository aliases', 'Additional alias-to-directory mappings used by the native repository resolver.', None, True),
    ('checkin', 'repository_display', 'Repository labels and colors', 'Display names and colors by repository alias. Example: {"custom_0":{"title":"Studio","color":"#607d8b"}}. Changes presentation only; repository paths stay separate.', None, False),
    ('checkin', 'version_padding', 'Version number width', 'Minimum number of digits in file naming, for example 3 produces v001.', '3', False),
    ('checkin', 'calculate_md5', 'File checksum mode', 'A non-empty value enables checksum calculation. Empty uses the project setting; if neither is set, checksums are skipped.', None, False),
    ('checkin', 'versionless_mode', 'Versionless files', 'Default uses copies on Windows and symbolic links on Linux. Symbolic links require Windows privileges or Developer Mode; hard links require files on the same volume. Updating replaces the alias, never writes through it.', None, False),
    ('checkin', 'win32_local_base_dir', 'Windows local base directory', 'Default local directory reported to Windows clients by get_base_dirs.', None, False),
    ('checkin', 'linux_local_base_dir', 'Linux local base directory', 'Default local directory reported to Linux clients by get_base_dirs.', None, False),
    ('checkin', 'win32_sandbox_dir', 'Windows sandbox directory', 'Working-file directory or alias mapping used by Windows client naming.', None, False),
    ('checkin', 'linux_sandbox_dir', 'Linux sandbox directory', 'Working-file directory or alias mapping used by Linux client naming.', None, False),
    ('checkin', 'win32_client_repo_dir', 'Windows client repository', 'Optional client-side repository directory or alias mapping for Windows.', None, False),
    ('checkin', 'linux_client_repo_dir', 'Linux client repository', 'Optional client-side repository directory or alias mapping for Linux.', None, False),
    ('checkin', 'win32_client_handoff_dir', 'Windows client handoff directory', 'Shared-folder path visible to Windows clients. Each ticket has a subdirectory; configure the server path to the same folder.', None, False),
    ('checkin', 'linux_client_handoff_dir', 'Linux client handoff directory', 'Shared-folder path visible to Linux clients. Each ticket has a subdirectory; configure the server path to the same folder.', None, False),
    ('checkin', 'win32_server_handoff_dir', 'Windows server handoff directory', 'Windows server path for handoff check-in. Falls back to the client path; relative paths resolve inside tactic_data.', None, False),
    ('checkin', 'linux_server_handoff_dir', 'Linux server handoff directory', 'Linux server path for handoff check-in. Falls back to the client path; relative paths resolve inside tactic_data.', None, False),
    ('checkin', 'sudo_no_password', 'Passwordless sudo for check-in', 'Legacy privilege elevation is not migrated. Enabling this option on Linux makes check-in refuse the operation.', 'false', False),
    ('schedule', 'mode', 'Task schedule mode', 'Optional automatic task scheduling: even divides elapsed time, even_day divides calendar days at noon, from_end_date schedules backwards from the parent due date. The project schedule/mode setting takes priority. Empty retains pipeline-generated dates; work calendars are not applied.', None, False),
    ('security', 'ticket_expiry', 'Ticket lifetime', 'Lifetime of new authentication tickets, for example 10 hour. Existing tickets keep their saved expiry.', '10 hour', False),
    ('security', 'inactive_ticket_expiry', 'Inactive ticket expiry', 'Interval used by the native ticket-renewal helper, for example 30 minute. This setting alone does not enable automatic renewal.', None, False),
    ('security', 'api_require_password', 'Require a password for batch login', 'Controls password requirements for native Batch login. It does not allow anonymous HTTP API access.', 'true', False),
    ('security', 'api_password', 'Batch API password', 'Optional shared credential for native Batch login. Never returned to the interface.', None, False),
    ('security', 'case_insensitive_login', 'Case-insensitive login', 'Compare account names without letter case when authenticating.', 'false', False),
    ('security', 'force_lowercase_login', 'Lowercase batch login', 'Convert the account name to lowercase before native Batch login.', 'false', False),
    ('security', 'invalid_login_attempts', 'Failed login limit', 'Optional failed-attempt threshold enforced by the native authentication logic.', None, False),
    ('security', 'password_expiry', 'Password expiry', 'Native password-age limit in days. Empty disables this additional check.', None, False),
    ('security', 'api_method_restricted', 'Restrict API methods', 'Apply native api_method access rules to guarded operations in addition to existing security checks.', 'false', False),
    ('security', 'api_cmd_restricted', 'Restrict command classes', 'Apply native api_cmd access rules to supported command and script execution paths.', 'false', False),
    ('security', 'api_widget_restricted', 'Restrict HTML widget classes', 'Apply native builtin widget rules and bound widget-key arguments. HTML execution still requires administrator access.', 'false', False),
    ('security', 'enable_fast_query', 'Enable fast query', 'Opt-in native fast_query for administrators. It does not bypass Security or allow reader access.', 'false', False),
    ('security', 'agent_mcp_enabled', 'Enable external MCP connections', 'Expose project-scoped MCP on this server listener. Disabled by default. Each connection requires its own expiring bearer token and selected tools; native account permissions still apply.', 'false', True),
    ('security', 'authenticate_class', 'Authentication class', 'Native authentication handler class. Unsupported custom handlers must be migrated before use.', 'pyasm.security.TacticAuthenticate', False),
    ('install', 'tmp_dir', 'Temporary files and logs', 'Server temporary directory. Worker and queue logs live in its log subdirectory.', 'temp', True),
    ('install', 'log_type', 'Legacy log type', 'Worker and queue logs currently use rotating files regardless of this legacy setting.', None, False),
    ('install', 'plugin_dir', 'Plugin directory', 'Directory for installed plugins, relative to the data directory unless absolute.', 'plugins', False),
)

GROUPS = (
    ('Services and workers', lambda section, key: section == 'services' and key not in ('start_port', 'ports')),
    ('Network', lambda section, key: (section, key) in (('install', 'hostname'), ('install', 'base_url'), ('services', 'start_port'), ('services', 'ports'))),
    ('Database', lambda section, key: section == 'database'),
    ('File repository', lambda section, key: section == 'checkin'),
    ('Task scheduling', lambda section, key: section == 'schedule'),
    ('Security', lambda section, key: section == 'security'),
    ('Directories and logs', lambda section, key: section == 'install' and key not in ('hostname', 'base_url')),
)

EDITABLE = {
    'services/enable': 'services', 'services/process_count': 'integer', 'services/thread_count': 'integer',
    'services/check_interval': 'number', 'services/worker_timeout': 'number', 'services/startup_timeout': 'number',
    'services/shutdown_timeout': 'number', 'services/restart_delay': 'number',
    'services/update_interval': 'number',
    'services/start_port': 'integer', 'services/ports': 'ports',
    'install/hostname': 'hostname', 'install/base_url': 'url', 'install/tmp_dir': 'path',
    'checkin/web_base_dir': 'paths', 'checkin/version_padding': 'padding', 'checkin/calculate_md5': 'checksum',
    'checkin/asset_base_dir': 'paths', 'checkin/base_dir_alias': 'paths',
    'checkin/versionless_mode': 'versionless',
    'checkin/repository_display': 'repositories',
    'schedule/mode': 'schedule', 'security/ticket_expiry': 'interval', 'security/inactive_ticket_expiry': 'interval',
    'security/api_require_password': 'boolean', 'security/api_password': 'secret',
    'security/case_insensitive_login': 'boolean', 'security/force_lowercase_login': 'boolean',
    'security/invalid_login_attempts': 'integer', 'security/password_expiry': 'integer',
    'security/api_method_restricted': 'boolean', 'security/api_cmd_restricted': 'boolean', 'security/api_widget_restricted': 'boolean',
    'security/enable_fast_query': 'boolean',
    'security/agent_mcp_enabled': 'boolean',
}
EDITABLE.update(('checkin/' + platform + '_' + key, 'paths' if key in ('sandbox_dir', 'client_repo_dir') else 'path')
                for platform in ('win32', 'linux')
                for key in ('local_base_dir', 'sandbox_dir', 'client_repo_dir', 'client_handoff_dir', 'server_handoff_dir'))
CHOICES = {
    'boolean': [('', 'Default'), ('true', 'Enabled'), ('false', 'Disabled')],
    'checksum': [('', 'Project setting'), ('true', 'Enabled')],
    'versionless': [('', 'Platform default'), ('copy', 'Copy'), ('symlink', 'Symbolic link'), ('hardlink', 'Hard link')],
    'schedule': [('', 'Pipeline dates'), ('even', 'Even elapsed time'), ('even_day', 'Even calendar days'),
                 ('from_end_date', 'From end date')],
}


def validate_setting(field, value):
    """Validate only the supported editable options; never execute config code."""
    from pyasm.common.config import ConfigException, normalize_config_path
    from pyasm.common import jsonloads, jsondumps
    kind = EDITABLE[field]
    hint = None
    if '\x00' in value or any(ord(char) < 32 for char in value):
        hint = 'Control characters are not allowed.'
    elif kind in CHOICES and value not in {choice[0] for choice in CHOICES[kind]}:
        hint = 'Choose a supported value.'
    elif kind == 'services' and value not in ('tactic', 'tactic|queue', 'tactic|files', 'tactic|queue|files'):
        hint = 'The web/API service must remain enabled.'
    elif kind in ('integer', 'padding') and value:
        if not value.isascii() or not value.isdecimal() or int(value) < 1:
            hint = 'Enter a positive whole number.'
        elif field == 'services/start_port' and int(value) > 65535:
            hint = 'Enter a port between 1 and 65535.'
        elif kind == 'padding' and int(value) > 32:
            hint = 'Version number width must be between 1 and 32.'
    elif kind == 'interval' and value and not re.fullmatch(r'[1-9][0-9]* (second|minute|hour|day|week|month|year)s?', value):
        hint = 'Use a positive whole number and second, minute, hour, day, week, month or year.'
    elif kind == 'hostname' and value:
        if ':' in value:
            import ipaddress
            try:
                ipaddress.IPv6Address(value)
            except ValueError:
                hint = 'Enter a hostname or IP address without a protocol or port.'
        elif not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', value):
            hint = 'Enter a hostname or IP address without a protocol or port.'
    elif kind == 'url' and value:
        try:
            parts = urlsplit(value)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or '\\' in value:
                hint = 'Enter an HTTP or HTTPS URL without credentials, query or fragment.'
            parts.port  # Check invalid/out-of-range port syntax.
        except ValueError:
            hint = 'Enter an HTTP or HTTPS URL without credentials, query or fragment.'
    elif kind == 'repositories' and value:
        try:
            entries = jsonloads(value)
            if not isinstance(entries, dict) or len(entries) > 100:
                raise ValueError()
            for alias, entry in entries.items():
                if not re.fullmatch(r'[A-Za-z0-9_.-]+', alias) or not isinstance(entry, dict) or set(entry) - {'title', 'color'}:
                    raise ValueError()
                if 'title' in entry and (not isinstance(entry['title'], str) or len(entry['title']) > 100):
                    raise ValueError()
                color = entry.get('color')
                if color is not None and not (isinstance(color, str) and re.fullmatch(r'#?[\da-fA-F]{6}', color) or isinstance(color, list) and len(color) == 3 and all(type(channel) is int and 0 <= channel <= 255 for channel in color)):
                    raise ValueError()
            value = jsondumps(entries)
        except (ValueError, TypeError):
            hint = 'Enter a JSON object mapping repository aliases to title and hex or RGB color.'
    elif kind in ('path', 'paths'):
        if value.startswith('{'):
            try:
                paths = jsonloads(value)
                if kind != 'paths' or not isinstance(paths, dict) or not paths or any(
                        not isinstance(alias, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', alias)
                        or not isinstance(path, str) or not path.strip() or any(ord(char) < 32 for char in path)
                        for alias, path in paths.items()):
                    raise ValueError()
                value = jsondumps(normalize_config_path(paths))
            except (ValueError, TypeError):
                hint = 'Enter a directory or a JSON object mapping aliases to directories.'
        else:
            value = normalize_config_path(value)
    if hint:
        raise ConfigException('Invalid configuration value', field=field, hint=hint)
    return value


def read_configuration():
    from pyasm.common import Environment
    security = Environment.get_security()
    if security is None or not security.is_admin():
        raise SecurityException('Server configuration requires administrator access')
    Config.reload_config()
    revision = Config.get_revision()
    path = Path(Config.get_config_path())
    writable = revision is not None and os.access(path, os.W_OK) and os.access(path.parent, os.W_OK)
    sections = {name: Config.get_section_values(name) for name in {row[0] for row in SETTINGS}}
    explicit_ports = bool(os.environ.get('TACTIC_PORTS') or sections['services'].get('ports', '').strip())
    groups = []
    for title, matches in GROUPS:
        entries = []
        for section, key, label, description, default, restart in SETTINGS:
            if not matches(section, key):
                continue
            raw = sections[section].get(key, '').strip()
            secret = key in ('password', 'password_file', 'api_password')
            entry = dict(path=section + '/' + key, label=label, description=description,
                         configured=bool(raw), value=None if secret or not raw else Config.get_value(section, key),
                         default=default, secret=secret, restart=restart, editable=False)
            field = entry['path']
            if field in EDITABLE:
                entry['editable'] = writable
                entry['input_type'] = EDITABLE[field]
                if entry['input_type'] in CHOICES:
                    entry['choices'] = [dict(value=value, label=label) for value, label in CHOICES[entry['input_type']]]
                if section == 'services' and key in ('process_count', 'start_port') and explicit_ports:
                    entry['editable'] = False
                    entry['note'] = 'Worker count and listener are determined by the explicit port list.'
            if section == 'database' or field == 'install/plugin_dir':
                entry['note'] = 'Changing this setting requires a separate data migration.'
            if field in ('checkin/asset_base_dir', 'checkin/base_dir_alias'):
                entry['note'] = 'Existing files must be present and unchanged in the new root. Restart the server after changing repository routes.'
            if field in ('install/log_type', 'security/authenticate_class', 'checkin/sudo_no_password'):
                entry['note'] = 'This option cannot be changed in the configuration editor.'
            if section == 'services' and key == 'ports' and os.environ.get('TACTIC_PORTS'):
                entry['environment_override'] = os.environ['TACTIC_PORTS']
                entry['editable'] = False
            if raw.startswith('{') and (section, key) in PATH_SETTINGS:
                from pyasm.common import jsondumps
                entry['value'] = jsondumps(Config.get_dict_value(section, key))
            if section == 'services' and key == 'enable':
                enabled = {name.strip() for name in re.split(r'[|,]', raw or default) if name.strip()}
                entry['services'] = [dict(name=name, enabled=name in enabled) for name in ('tactic', 'queue', 'files')]
            entries.append(entry)
        groups.append(dict(title=title, settings=entries))
    known = {(section, key) for section, key, *_ in SETTINGS}
    xml = Config.get_xml_data()
    root = xml.get_root_node()
    undocumented = []
    for section in root:
        if not isinstance(section.tag, str):
            continue
        for key in Config.get_section_values(section.tag):
            if (section.tag, key) not in known:
                # Unknown settings may contain credentials. Return names only.
                undocumented.append(section.tag + '/' + key)
    from tactic_stream.server.server_events import read_event_clients
    return dict(config_path=path.as_posix(), data_dir=Environment.get_data_dir(), revision=revision, writable=writable,
                groups=groups, undocumented=sorted(undocumented), event_clients=read_event_clients(Environment.get_data_dir()))


def save_configuration(changes, revision):
    from pyasm.common import Environment
    from pyasm.common.config import ConfigException, ConfigConflict
    from tactic_stream.server.startup import parse_service_config
    security = Environment.get_security()
    if security is None or not security.is_admin():
        raise SecurityException('Server configuration requires administrator access')
    if not isinstance(revision, str) or not revision or len(revision) > 256:
        raise ValueError('A configuration revision is required')
    if not isinstance(changes, dict) or not changes or len(changes) > len(EDITABLE):
        raise ValueError('Editable configuration settings are required')
    for field, value in changes.items():
        if field not in EDITABLE or not isinstance(value, str) or len(value) > 4096:
            raise ConfigException('Unknown or invalid configuration setting', field=field if isinstance(field, str) else None,
                                  hint='Choose a supported setting with at most 4096 characters.')
    changes = {field: validate_setting(field, value if EDITABLE[field] == 'secret' else value.strip())
               for field, value in changes.items()}
    Config.get_config_path(no_exception=False)
    Config.reload_config()
    if Config.get_revision() != revision:
        raise ConfigConflict('Configuration changed since it was loaded')
    sections = {field.split('/')[0]: Config.get_section_values(field.split('/')[0]) for field in changes}
    updated = Config.get_section_values('services')
    for field, value in changes.items():
        section, key = field.split('/')
        if section == 'services':
            updated[key] = value
    explicit_ports = os.environ.get('TACTIC_PORTS') or updated.get('ports', '').strip()
    if os.environ.get('TACTIC_PORTS') and 'services/ports' in changes:
        raise ConfigException('Ports are overridden by the environment', field='services/ports',
                              hint='Remove the TACTIC_PORTS environment override before editing ports.')
    for field in ('services/process_count', 'services/start_port'):
        if field in changes and explicit_ports:
            raise ConfigException('Explicit ports determine worker count and listener', field=field,
                                  hint='Clear the explicit port list before editing worker count or first port.')
    expanded = {key: os.path.expandvars(value) for key, value in updated.items()}
    parse_service_config(expanded, use_environment=False)
    parse_service_config(expanded)  # Also validate an active TACTIC_PORTS override.
    roots = Environment.get_asset_dirs()
    roots.setdefault('default', Environment.get_asset_dir())
    root_fields = ('checkin/asset_base_dir', 'checkin/base_dir_alias')
    if any(field in changes for field in root_fields):
        from pyasm.common import jsonloads
        from pyasm.search import Search
        import hashlib
        updated_roots = {}
        for field in root_fields:
            section, key = field.split('/')
            raw = os.path.expandvars(changes.get(field, sections['checkin'].get(key, ''))).strip()
            updated_roots.update(jsonloads(raw) if raw.startswith('{') else {'default': raw} if raw else {})
        updated_roots.setdefault('default', Environment._directory('assets'))
        updated_roots.setdefault('plugins', Environment.get_plugin_dir())
        updated_roots = {alias: Environment._directory(path) for alias, path in updated_roots.items()}
        changed_roots = {alias for alias in set(roots) | set(updated_roots) if roots.get(alias) != updated_roots.get(alias)}
        for alias in changed_roots:
            path = updated_roots.get(alias)
            if path and not Path(path).is_dir():
                raise ConfigException('Repository folder is not available', field='checkin/asset_base_dir', hint='Choose an existing server directory.')
        for file in Search('sthpw/file').get_sobjects():
            alias = file.get_value('base_dir_alias') or 'default'
            if alias not in changed_roots:
                continue
            relative = Path(file.get_value('relative_dir') or '') / file.get_value('file_name')
            target_root = updated_roots.get(alias)
            target = Path(target_root) / relative if target_root else None
            source = Path(roots[alias]) / relative if alias in roots else None
            matches = target is not None and target.resolve().is_relative_to(Path(target_root).resolve()) and target.exists()
            if matches and source and source.is_file():
                if not target.is_file():
                    matches = False
                else:
                    with source.open('rb') as old, target.open('rb') as new:
                        matches = hashlib.file_digest(old, 'sha256').digest() == hashlib.file_digest(new, 'sha256').digest()
            if matches and source and source.is_dir():
                matches = target.is_dir()
                for child in source.rglob('*') if matches else []:
                    copied = target / child.relative_to(source)
                    if child.is_dir():
                        matches = copied.is_dir()
                    elif child.is_file() and copied.is_file():
                        with child.open('rb') as old, copied.open('rb') as new:
                            matches = hashlib.file_digest(old, 'sha256').digest() == hashlib.file_digest(new, 'sha256').digest()
                    else:
                        matches = False
                    if not matches:
                        break
            if not matches:
                raise ConfigException('Repository change would make existing files unavailable', field='checkin/asset_base_dir', hint='Copy the existing files to the new root before saving. Referenced aliases cannot be removed.')
        roots = updated_roots
    if any(field in changes for field in (*root_fields, 'checkin/web_base_dir')):
        from pyasm.common import jsonloads
        from tactic_stream.server.app import repository_web_paths
        address = os.path.expandvars(changes.get('checkin/web_base_dir', sections['checkin'].get('web_base_dir', '')))
        web_dirs = jsonloads(address) if address.startswith('{') else {'default': address} if address else {}
        try:
            repository_web_paths(roots, web_dirs)
        except ValueError:
            raise ConfigException('Invalid repository web paths', field='checkin/web_base_dir',
                                  hint='Use distinct repository URLs with existing aliases, outside application routes.') from None
    changed = [field for field, value in changes.items() if sections[field.split('/')[0]].get(field.split('/')[1], '') != value]
    for field in changed:
        section, key = field.split('/')
        Config.set_value(section, key, changes[field])
    if changed:
        Config.save_config()
    result = read_configuration()
    restart_fields = {section + '/' + key for section, key, *_, restart in SETTINGS if restart}
    result.update(saved=bool(changed), restart_required=bool(set(changed) & restart_fields))
    return result
