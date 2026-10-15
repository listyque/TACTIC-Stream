# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""TACTIC Config on the owned server's config/tactic-conf.xml.

Adapted from pyasm/common/config.py. The request cache and v1/v2 XML formats
are retained; dictionary values are parsed without executing configuration.
"""
import ast
import copy
from contextlib import contextmanager
import errno
import hashlib
from importlib.resources import files
import os
from pathlib import Path
import tempfile
import time
import xml.etree.ElementTree as ET
from pyasm.common.common import Base, jsondumps, jsonloads
from pyasm.common.lxml_wrapper import Xml


PATH_SETTINGS = {('install', key) for key in ('tmp_dir', 'plugin_dir')}
PATH_SETTINGS.update({('database', 'password_file'), ('checkin', 'asset_base_dir'),
                      ('checkin', 'base_dir_alias'), ('checkin', 'web_base_dir')})
PATH_SETTINGS.update(('checkin', platform + '_' + key) for platform in ('win32', 'linux')
                     for key in ('local_base_dir', 'local_repo_dir', 'sandbox_dir', 'client_repo_dir',
                                 'client_handoff_dir', 'server_handoff_dir'))


def normalize_config_path(value):
    """Forward slashes for filesystem paths, including client paths and aliases.

    Do not resolve client paths on the server or collapse UNC/URL prefixes.
    """
    if isinstance(value, dict):
        return {key: normalize_config_path(path) for key, path in value.items()}
    return value.replace('\\', '/') if isinstance(value, str) else value


class ConfigException(Exception):
    def __init__(self, message, *, field=None, hint=None):
        super().__init__(message)
        self.field = field
        self.hint = hint


class ConfigConflict(ConfigException):
    pass


class Config(Base):
    CONFIG_KEY = 'Config:data'
    _startup_cache = {}
    _file_cache = None

    @classmethod
    def _cache(cls):
        from pyasm.search.search import _context
        context = _context.get(None)
        cache = context.container.info if context else cls._startup_cache
        path = cls.get_config_path()
        if cache.get('Config:path') != path:
            cache.pop(cls.CONFIG_KEY, None)
            cache.pop('Config:xml_data', None)
            cache.pop('Config:revision', None)
            cache.pop('Environment:directories', None)
            cache['Config:path'] = path
        return cache

    @classmethod
    def get_value(cls, module_name, key, no_exception=True, default='', use_cache=True, sub_key=None):
        cache = cls._cache()
        data = cache.get(cls.CONFIG_KEY)
        if data is None:
            data = {}
            cache[cls.CONFIG_KEY] = data
        cache_key = '%s:%s' % (module_name, key)
        if sub_key:
            cache_key += ':' + sub_key
        value = data.get(cache_key)
        if not use_cache or value is None:
            xml = cls.get_xml_data()
            xpath = 'config/%s/%s' if xml.get_value('config/@version') else 'config/%s/@%s'
            value = os.path.expandvars(xml.get_value(xpath % (module_name, key)))
            value = (value or default).strip()
            if not no_exception and value == '':
                raise ConfigException('config value [%s/%s] is empty or does not exist' % (module_name, key))
            if sub_key:
                try:
                    value = ast.literal_eval(value).get(sub_key)
                except (ValueError, SyntaxError, AttributeError):
                    pass
            if (module_name, key) in PATH_SETTINGS and not (isinstance(value, str) and value.startswith('{')):
                value = normalize_config_path(value)
            data[cache_key] = value
        return value

    @classmethod
    def get_dict_value(cls, module_name, key, no_exception=True, default='', use_cache=True):
        value = cls.get_value(module_name, key, no_exception, default, use_cache)
        if not value:
            return {}
        try:
            result = jsonloads(value)
        except ValueError:
            result = {'default': value.strip()}
        return normalize_config_path(result) if (module_name, key) in PATH_SETTINGS else result

    @staticmethod
    def get_xml_data(use_cache=True):
        cache = Config._cache()
        xml = cache.get('Config:xml_data') if use_cache else None
        if xml is None:
            path = Path(Config.get_config_path())
            try:
                stat = path.stat()
                fingerprint = (path, stat.st_mtime_ns, stat.st_size, stat.st_ino)
            except FileNotFoundError:
                if os.environ.get('TACTIC_CONFIG_PATH') or os.environ.get('TACTIC_TMP_CONFIG_PATH'):
                    raise ConfigException('Explicit configuration file does not exist: %s' % path)
                fingerprint = (path, None, None, None)
            saved = Config._file_cache
            if not use_cache or saved is None or saved[0] != fingerprint:
                text, revision = read_config_file(path) if fingerprint[1] is not None else ('<config version="2"/>', None)
                if '<!DOCTYPE' in text or '<!ENTITY' in text:
                    raise ConfigException('DTD/entities are not accepted')
                # Cache just one parsed file; never share mutable request XML.
                saved = (fingerprint, ET.fromstring(text, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))), revision)
                Config._file_cache = saved
            xml = Xml(doc=copy.deepcopy(saved[1]))
            cache['Config:xml_data'] = xml
            cache['Config:revision'] = saved[2]
        return xml

    @staticmethod
    def get_revision():
        Config.get_xml_data()
        return Config._cache().get('Config:revision')

    @staticmethod
    def reload_config():
        from pyasm.search.search import _context
        context = _context.get(None)
        if context:
            context.container.info.pop('Config:resolved_path', None)
            context.container.info.pop('Environment:directories', None)
        Config._cache()[Config.CONFIG_KEY] = {}
        Config.get_xml_data(use_cache=False)

    @staticmethod
    def get_section_values(section_name):
        xml = Config.get_xml_data()
        node = xml.get_node('config/%s' % section_name)
        if node is None:
            return {}
        if not xml.get_value('config/@version'):
            return dict(node.attrib)
        return {child.tag: child.text or '' for child in node if isinstance(child.tag, str)}

    @staticmethod
    def set_value(module_name, key, value, no_exception=True, create=True):
        xml = Config.get_xml_data()
        parent = xml.get_node('config/%s' % module_name)
        node = xml.get_node('config/%s/%s' % (module_name, key))
        if node is None:
            if not no_exception:
                raise ConfigException('No node for module [%s] with key [%s] in TACTIC config file' % (module_name, key))
            if not create:
                return
            if parent is None:
                parent = xml.create_element(module_name, node=xml.get_root_node())
            node = xml.create_element(key, node=parent)
        if isinstance(value, dict):
            value = jsondumps(value)
        elif isinstance(value, str) and value.startswith('{'):
            value = jsondumps(ast.literal_eval(value))
        else:
            value = str(value)
        # Attribute-based v1 configuration must remain readable after an edit.
        if not xml.get_value('config/@version'):
            parent.set(key, value)
        node.text = value
        Config._cache()[Config.CONFIG_KEY] = {}
        Config._cache().pop('Environment:directories', None)

    @classmethod
    def get_config_path(cls, no_exception=True):
        from pyasm.search.search import _context
        context = _context.get(None)
        data_dir = context.store.data_dir if context else Path(os.environ.get('TACTIC_DATA_DIR', 'data'))
        source = os.environ.get('TACTIC_TMP_CONFIG_PATH') or os.environ.get('TACTIC_CONFIG_PATH') or str(data_dir / 'config/tactic-conf.xml')
        cached = context.container.info.get('Config:resolved_path') if context else None
        if cached and cached[0] == source:
            path = cached[1]
        else:
            path = Path(source).expanduser().resolve()
            if context:
                context.container.info['Config:resolved_path'] = (source, path)
        if not no_exception and not path.is_file():
            raise ConfigException('Config path [%s] does not exist' % path)
        return path.as_posix()

    @classmethod
    def get_config_dir(cls):
        return Path(cls.get_config_path()).parent.as_posix()

    @staticmethod
    def get_default_config_path():
        return str(files('tactic_stream') / 'config/tactic-conf.xml').replace('\\', '/')

    @staticmethod
    def save_config():
        from pyasm.common.environment import Environment
        security = Environment.get_security()
        if security is None or not security.is_admin():
            raise ConfigException('Saving server configuration requires administrator access')
        path = Path(Config.get_config_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        save_config_file(path, Config.get_xml_data().to_string(), expected_revision=Config.get_revision(), backup=True)
        Config.reload_config()


def read_config_file(path):
    with Path(path).open('rb') as source:
        data = source.read()
        stat = os.fstat(source.fileno())
    revision = '%s:%s:%s' % (hashlib.sha256(data).hexdigest(), stat.st_mtime_ns, stat.st_ino)
    return data.decode('utf-8'), revision


@contextmanager
def config_file_lock(path):
    """One cooperative writer across threads/processes, on Windows and Linux."""
    with path.with_name(path.name + '.lock').open('a+b') as lock:
        if os.name == 'nt' and os.fstat(lock.fileno()).st_size == 0:
            lock.write(b'0')
            lock.flush()
        deadline = time.monotonic() + 5
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise ConfigConflict('Configuration writer is busy') from None
                time.sleep(.02)
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


_UNCHECKED_REVISION = object()


def save_config_file(path, text, *, expected_revision=_UNCHECKED_REVISION, backup=False):
    """Publish a complete XML file, even if the writer is interrupted."""
    path = Path(path)
    with config_file_lock(path):
        exists = path.exists()
        current, revision = read_config_file(path) if exists else (None, None)
        if expected_revision is not _UNCHECKED_REVISION and expected_revision != revision:
            raise ConfigConflict('Configuration was changed by another writer')
        if text == current:
            return
        mode = path.stat().st_mode & 0o777 if exists else 0o600
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='', dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                output.write(text)
                output.flush()
                os.fsync(output.fileno())
            if backup and exists:
                save_config_file(path.with_name(path.name + '.previous'), current)
            temporary.chmod(mode)
            os.replace(temporary, path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def initialize_config(data_dir, config_path=None):
    data_dir = Path(data_dir).resolve()
    path = Path(config_path) if config_path else data_dir / 'config/tactic-conf.xml'
    template = (files('tactic_stream') / 'config/tactic-conf.xml').read_text(encoding='utf-8')
    defaults = ET.fromstring(template).find('checkin')
    defaults.find('asset_base_dir').text = (data_dir / 'assets').as_posix()
    exists = path.exists()
    text, revision = read_config_file(path) if exists else (template, None)
    if '<!DOCTYPE' in text or '<!ENTITY' in text:
        raise ConfigException('DTD/entities are not accepted')
    root = ET.fromstring(text, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    checkin = root.find('checkin')
    changed = not exists
    if checkin is None:
        checkin = ET.SubElement(root, 'checkin')
        changed = True
    # Upgrade the previously incomplete Stream template at startup, not in API
    # responses. Retain configured values, other sections and both XML formats.
    for node in defaults:
        if root.get('version'):
            existing = checkin.find(node.tag)
            if existing is None:
                checkin.append(copy.deepcopy(node))
                changed = True
            elif node.tag == 'asset_base_dir' and not (existing.text or '').strip():
                existing.text = node.text
                changed = True
        elif node.tag not in checkin.attrib or (node.tag == 'asset_base_dir' and not checkin.get(node.tag)):
            checkin.set(node.tag, node.text or '')
            changed = True
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        save_config_file(path, ET.tostring(root, encoding='unicode'), expected_revision=revision)
    return path
