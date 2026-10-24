from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from tools.prepare_legacy_examples import ROOT, prepare, repair_vfx_config


class LegacyExamples(unittest.TestCase):
    def test_known_game_repair_preserves_every_other_source_byte(self):
        source = ROOT.parent / 'legacy/src/install/start/templates'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'examples'
            result = prepare(source, output)
            self.assertEqual((output / 'vfx-1.0.0.zip').read_bytes(), (source / 'vfx-1.0.0.zip').read_bytes())
            with zipfile.ZipFile(source / 'game-1.0.0.zip') as old, zipfile.ZipFile(output / 'game-1.0.0-stream.1.zip') as new:
                self.assertEqual(old.namelist(), new.namelist())
                for name in old.namelist():
                    before, after = old.read(name), new.read(name)
                    if name == 'game/sthpw_pipeline.spt':
                        self.assertEqual(before.count(b"task_pipeline='game_status_default'"), 6)
                        self.assertEqual(after, before.replace(b"task_pipeline='game_status_default'", b"task_pipeline='game/status_default'"))
                    else:
                        self.assertEqual(after, before, name)
            self.assertEqual(result['repairs']['game-1.0.0-stream.1.zip']['references'], 6)
            with zipfile.ZipFile(source / 'vfx-1.0.0.zip') as old, zipfile.ZipFile(output / 'vfx-1.0.0-stream.1.zip') as new:
                self.assertEqual(old.namelist(), new.namelist())
                for name in old.namelist():
                    before, after = old.read(name), new.read(name)
                    if name == 'vfx/config_widget_config.spt':
                        self.assertNotEqual(before, after)
                        self.assertEqual(after.decode('utf-8'), repair_vfx_config(before.decode('utf-8')))
                        for obsolete in ('FrameRangeWdg', 'FrameInputWdg', 'FrameAction', 'AssetDetailWdg'):
                            self.assertNotIn(obsolete.encode(), after)
                        self.assertEqual(repair_vfx_config(after.decode('utf-8')), after.decode('utf-8'))
                    else:
                        self.assertEqual(after, before, name)
            with self.assertRaises(FileExistsError):
                prepare(source, output)
            changed = Path(directory) / 'changed'
            shutil.copytree(source, changed)
            with (changed / 'vfx-1.0.0.zip').open('ab') as stream:
                stream.write(b'changed source')
            rejected = Path(directory) / 'rejected'
            with self.assertRaises(ValueError):
                prepare(changed, rejected)
            self.assertFalse(rejected.exists())
