"""Nested Frame copies must ship completely and retain layer boundaries."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import sync_tactic_frame as frame


class FrameSyncTests(unittest.TestCase):
    def setUp(self):
        workspace = Path(__file__).resolve().parents[1]
        self.temporary = tempfile.TemporaryDirectory(prefix='frame-sync-', dir=workspace / '.tmp')
        self.root = Path(self.temporary.name)
        assert self.root.resolve().is_relative_to((workspace / '.tmp').resolve())
        self.addCleanup(self.temporary.cleanup)
        self.source = self.root / 'stream'
        (self.source / 'core').mkdir(parents=True)
        (self.source / 'controls/graph').mkdir(parents=True)
        (self.source / 'core/frame.mjs').write_text('export const value = 1;')
        (self.source / 'controls/graph/graph.mjs').write_text('import {value} from "../../core/frame.mjs"; export {value};')
        self.handler = self.root / 'handler'
        self.patch = patch.object(frame, 'SOURCE', self.source)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_nested_copy_and_manifest_and_independent_readback(self):
        frame.sync(self.handler, copy_from='stream')
        target = self.handler / 'thlib/ui/qml/tactic_frame'
        self.assertEqual((target / 'controls/graph/graph.mjs').read_bytes(), (self.source / 'controls/graph/graph.mjs').read_bytes())
        frame.sync(self.handler, check=True)
        (target / 'controls/graph/graph.mjs').write_text('export const value = 2;')
        with self.assertRaisesRegex(AssertionError, 'copies differ'):
            frame.sync(self.handler, check=True)

    def test_copy_does_not_hide_or_delete_an_old_flat_module(self):
        frame.sync(self.handler, copy_from='stream')
        old = self.handler / 'thlib/ui/qml/tactic_frame/graph.mjs'
        old.write_text('export const stale = true;')
        with self.assertRaisesRegex(AssertionError, 'module lists'):
            frame.sync(self.handler, copy_from='stream')
        self.assertTrue(old.exists())

    def test_controls_cannot_import_feature_implementations(self):
        (self.source / 'features').mkdir()
        (self.source / 'features/admin.mjs').write_text('export const x = 1;')
        (self.source / 'controls/graph/graph.mjs').write_text('import "../../features/admin.mjs";')
        with self.assertRaisesRegex(AssertionError, 'Control depends on features'):
            frame.sync(self.handler, copy_from='stream')

    def test_a_relative_import_cannot_escape_the_product_copy(self):
        (self.root / 'outside.mjs').write_text('export const x = 1;')
        (self.source / 'core/frame.mjs').write_text('import "../../outside.mjs";')
        with self.assertRaisesRegex(AssertionError, 'External Frame import'):
            frame.sync(self.handler, copy_from='stream')

    def test_ui_captions_named_from_are_not_module_imports(self):
        (self.source / 'core/frame.mjs').write_text('export const fields = ["from", "to"];')
        frame.sync(self.handler, copy_from='stream')


if __name__ == '__main__':
    unittest.main()
