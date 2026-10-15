import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from pyasm.search.storage import Store
from pyasm.common import Config, Container, Environment
from pyasm.search import FileUndo
from pyasm.search.search import RequestContext, request_context


class EnvironmentPaths(unittest.TestCase):
    def test_copy_guard_resolves_regular_source_parent_once_but_rechecks_leaf_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.bin'
            source.write_bytes(b'source')
            with request_context(RequestContext(Store(root), 'admin')):
                with patch.object(os.path, 'realpath', wraps=os.path.realpath) as resolve:
                    for index in range(10):
                        FileUndo._check_source(str(source), str(root / ('copy_%d.bin' % index)))
                    source_calls = [call for call in resolve.call_args_list if call.args[0] == str(source)]
                    self.assertEqual(source_calls, [])
                source.unlink()
                target = root / 'target.bin'
                target.write_bytes(b'target')
                # A reparse leaf must use full resolution even after its parent was cached.
                import stat
                info = Mock(st_mode=stat.S_IFREG, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
                with patch('os.lstat', return_value=info), patch.object(os.path, 'realpath', return_value=str(target)):
                    with self.assertRaisesRegex(ValueError, 'onto itself'):
                        FileUndo._check_source(str(source), str(target))

    def test_selected_asset_root_preserves_aliases_without_resolving_unused_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with request_context(RequestContext(Store(root), 'admin')):
                Config.set_value('install', 'plugin_dir', 'extensions')
                Config.set_value('checkin', 'asset_base_dir', {'default': 'repo', 'archive': 'old'})
                Config.set_value('checkin', 'base_dir_alias', {'archive': 'archive', 'disabled': ''})
                with patch.object(Environment, '_directory', wraps=Environment._directory) as resolve:
                    self.assertEqual(Environment.get_asset_dir(), (root / 'repo').as_posix())
                    resolve.assert_called_once_with('repo')
                self.assertEqual(Environment.get_asset_dir(alias='archive'), (root / 'archive').as_posix())
                self.assertEqual(Environment.get_asset_dir(alias='plugins'), (root / 'extensions').as_posix())
                for alias in ('disabled', 'missing'):
                    self.assertEqual(Environment.get_asset_dir(alias=alias), (root / 'assets').as_posix())
                file = Mock()
                file.get_value.return_value = 'archive'
                self.assertEqual(Environment.get_asset_dir(file, alias='plugins'), (root / 'archive').as_posix())
                Config.set_value('checkin', 'base_dir_alias', {'plugins': 'plugin_override'})
                self.assertEqual(Environment.get_asset_dir(alias='plugins'), (root / 'plugin_override').as_posix())
                Config.set_value('checkin', 'base_dir_alias', {'plugins': ''})
                self.assertEqual(Environment.get_asset_dir(alias='plugins'), (root / 'assets').as_posix())

    def test_directory_cache_is_bounded_and_evicted_paths_still_resolve(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with request_context(RequestContext(Store(root), 'admin')):
                for index in range(300):
                    self.assertEqual(Environment._directory('parent_%d' % index),
                                     (root / ('parent_%d' % index)).as_posix())
                self.assertLessEqual(len(Container.get_full_dict('Environment:directories')), 256)
                self.assertEqual(Environment._directory('parent_0'), (root / 'parent_0').as_posix())
                self.assertLessEqual(len(Container.get_full_dict('Environment:directories')), 256)

    def test_file_copy_guard_resolves_shared_parent_once_and_keeps_self_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.bin'
            source.write_bytes(b'source')
            parent = root / 'destinations'
            parent.mkdir()
            with request_context(RequestContext(Store(root), 'admin')):
                with patch.object(os.path, 'realpath', wraps=os.path.realpath) as resolve:
                    for index in range(10):
                        FileUndo._check_source(str(source), str(parent / ('file_%d.bin' % index)))
                    calls = [call for call in resolve.call_args_list
                             if os.path.normcase(os.path.abspath(call.args[0])) == os.path.normcase(str(parent))]
                    self.assertEqual(len(calls), 1)
                with self.assertRaisesRegex(ValueError, 'onto itself'):
                    FileUndo._check_source(str(source), str(source))
                with self.assertRaisesRegex(ValueError, 'inside itself'):
                    FileUndo._check_source(str(parent), str(parent / 'nested' / 'file.bin'))
                with self.assertRaises(FileNotFoundError):
                    FileUndo._check_source(str(root / 'missing.bin'), str(parent / 'new.bin'))

    def test_roots_are_reused_only_in_the_current_request_and_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            store = Store(root)
            resolve = Path.resolve
            calls = []
            def counted(path, *args, **kwargs):
                calls.append(path)
                return resolve(path, *args, **kwargs)
            with patch.object(Path, 'resolve', counted):
                with request_context(RequestContext(store, 'admin')):
                    first = Environment._directory('assets')
                    self.assertEqual(Environment._directory(str(root / 'assets')), first)
                    self.assertEqual(calls.count(root / 'assets'), 1)
                    Config.set_value('checkin', 'asset_base_dir', {'default': 'other', 'studio': 'assets'})
                    roots = Environment.get_asset_dirs()
                    self.assertEqual(roots['default'], (root / 'other').as_posix())
                    self.assertEqual(roots['studio'], first)
                    self.assertEqual(calls.count(root / 'assets'), 2)
                    Config.reload_config()
                    self.assertEqual(Environment.get_asset_dir(), first)
                    self.assertEqual(calls.count(root / 'assets'), 3)
                with request_context(RequestContext(store, 'admin')):
                    self.assertEqual(Environment._directory('assets'), first)
                    self.assertEqual(calls.count(root / 'assets'), 4)
                other = root / 'other_data'
                other.mkdir()
                with request_context(RequestContext(Store(other), 'admin')):
                    self.assertEqual(Environment._directory('assets'), (other / 'assets').as_posix())

    def test_missing_roots_refresh_when_created_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root)
            with request_context(RequestContext(store, 'admin')):
                expected = (root / 'assets' / 'missing').as_posix()
                self.assertEqual(Environment._directory('assets/missing'), expected)
                (root / 'assets').mkdir()
                self.assertEqual(Environment._directory('assets/missing'), expected)
                (root / 'assets' / 'missing').mkdir()
                self.assertEqual(Environment._directory('assets/missing'), expected)
                (root / 'assets' / 'missing').rename(root / 'assets' / 'old')
                (root / 'assets' / 'missing').mkdir()
                self.assertEqual(Environment._directory('assets/missing'), expected)

    def test_link_retarget_and_target_move_refresh_canonical_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root)
            link = root / 'alias'
            first, second = root / 'first', root / 'second'
            first.mkdir(); second.mkdir()
            def point_to(target):
                if os.name == 'nt':
                    subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                   check=True, capture_output=True)
                else:
                    link.symlink_to(target, target_is_directory=True)
            def remove_link():
                if os.name == 'nt':
                    link.rmdir()
                else:
                    link.unlink()
            point_to(first)
            try:
                with request_context(RequestContext(store, 'admin')):
                    self.assertEqual(Environment._directory('alias'), first.as_posix())
                    self.assertEqual(Environment._directory('alias/missing'), (first / 'missing').as_posix())
                    source = first / 'source.bin'
                    source.write_bytes(b'source')
                    with self.assertRaisesRegex(ValueError, 'onto itself'):
                        FileUndo._check_source(str(source), str(link / source.name))
                    with self.assertRaisesRegex(ValueError, 'onto itself'):
                        FileUndo._check_source(str(link / source.name), str(source))
                    remove_link(); point_to(second)
                    self.assertEqual(Environment._directory('alias'), second.as_posix())
                    self.assertEqual(Environment._directory('alias/missing'), (second / 'missing').as_posix())
                    FileUndo._check_source(str(source), str(link / source.name))
                    source = second / 'source.bin'
                    source.write_bytes(b'second')
                    with self.assertRaisesRegex(ValueError, 'onto itself'):
                        FileUndo._check_source(str(source), str(link / source.name))
                    with self.assertRaisesRegex(ValueError, 'onto itself'):
                        FileUndo._check_source(str(link / source.name), str(source))
                    moved = root / 'moved'
                    second.rename(moved)
                    remove_link(); point_to(moved)
                    self.assertEqual(Environment._directory('alias'), moved.as_posix())
                    self.assertEqual(Environment._directory('alias/missing'), (moved / 'missing').as_posix())
            finally:
                remove_link()
