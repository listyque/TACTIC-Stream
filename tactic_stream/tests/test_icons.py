import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import test_read_parity as read_tests
import test_checkin as checkin_tests
from pyasm.biz import IconCreator, Project, Snapshot
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import FileUndo, Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api


class IconParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='icon_contract', project='admin', name='image_previews')]

    new_result = checkin_tests.CheckinParity.new_result

    def test_image_fixes_and_late_failure_restore_previews(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            ticket = {'ticket': api.get_ticket('admin', 'private-test-password'), 'project': 'admin'}
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', ticket['ticket'])
                source = Path(Environment.get_upload_dir()) / 'image.png'
                output = source.parent / 'preview.png'
                output.write_bytes(b'previous preview')
                command = Command()
                def fail():
                    command.get_transaction().set_sync(False)
                    Image.new('LA', (32, 16), (40, 0)).save(source)
                    creator = IconCreator(str(source))
                    creator._resize_image(str(source), str(output), (120, 100))
                    with Image.open(output) as image:
                        self.assertEqual(image.size, (32, 16))
                        self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
                    raise ValueError('late image failure')
                command.execute = fail
                with self.assertRaisesRegex(ValueError, 'late image failure'):
                    Command.execute_cmd(command)
                self.assertEqual(output.read_bytes(), b'previous preview')
                # A failed encoder cannot consume an old preview or publish an incomplete file.
                command = Command()
                def encoding_error():
                    command.get_transaction().set_sync(False)
                    with patch.object(Image.Image, 'save', side_effect=ValueError('encoder failed')):
                        IconCreator(str(source))._resize_image(str(source), str(output), (120, 100))
                command.execute = encoding_error
                with self.assertRaisesRegex(ValueError, 'encoder failed'):
                    Command.execute_cmd(command)
                self.assertEqual(output.read_bytes(), b'previous preview')
                # Palette transparency, small portraits, square bounds and mirrored EXIF.
                command = Command()
                def fixes():
                    command.get_transaction().set_sync(False)
                    for mode in ('LA', 'P', 'RGBA'):
                        image = Image.new(mode, (32, 64))
                        if mode == 'P':
                            image.info['transparency'] = 0
                        image.save(source)
                        IconCreator(str(source))._resize_image(str(source), str(output), (120, 100))
                        with Image.open(output) as result:
                            self.assertEqual(result.size, (32, 64))
                            self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
                    Image.new('RGB', (800, 800)).save(source)
                    creator = IconCreator(str(source))
                    creator.execute()
                    with Image.open(creator.get_web_path()) as result:
                        self.assertEqual(result.size, (480, 480))
                    with Image.open(creator.get_icon_path()) as result:
                        self.assertEqual(result.size, (100, 100))
                    first_paths = (creator.get_web_path(), creator.get_icon_path())
                    creator.execute()
                    self.assertEqual((creator.get_web_path(), creator.get_icon_path()), first_paths)
                    with patch('pyasm.biz.project.Project.get_project_name', return_value='one'):
                        for value, expected in (('320x-1', (320, -1)), ('320', (320, -1)),
                                                ('320x240', (320, 240)), ('0x100', (640, 480))):
                            with patch('pyasm.biz.prod_setting.ProdSetting.get_value_by_key', return_value=value):
                                self.assertEqual(creator.get_web_file_size(), expected)
                    image = Image.new('RGB', (2, 1))
                    image.putdata([(255, 0, 0), (0, 0, 255)])
                    image.getexif()[274] = 2
                    self.assertEqual(creator.correct_orientation(image).getpixel((0, 0)), (0, 0, 255))
                    document = source.parent / 'normal.txt'
                    document.write_text('normal file')
                    self.assertEqual(IconCreator.add_icons([str(document)]), ([], []))
                    pdf = source.parent / 'unported.pdf'
                    pdf.write_bytes(b'pdf')
                    with self.assertRaises(UnsupportedContract):
                        IconCreator(str(pdf)).execute()
                    core_source = source.parent / 'core.png'
                    Image.new('RGB', (800, 400)).save(core_source)
                    snapshot = Snapshot.create(Project.get(), 'file', 'icon_core_append')
                    snapshot.add_file(str(core_source), mode='move', create_icon=True)
                    search = Search('sthpw/file')
                    search.add_filter('snapshot_code', snapshot.get_code())
                    self.assertEqual(sorted(file.get_type() for file in search.get_sobjects()), ['icon', 'main', 'web'])
                command.execute = fixes
                Command.execute_cmd(command)
                # A failure after completed check-in rolls back metadata and all preview replacements.
                Image.new('RGB', (800, 400), (40, 80, 120)).save(source)
                web = source.parent / 'image_web.jpg'
                icon = source.parent / 'image_icon.png'
                web.write_bytes(b'old web')
                icon.write_bytes(b'old icon')
                # Encoder IO failure aborts the check-in, instead of silently succeeding without previews.
                command = Command()
                def io_failure():
                    command.get_transaction().set_sync(False)
                    with patch.object(Image.Image, 'save', side_effect=OSError('preview IO failure')):
                        api.simple_checkin(ticket, Project.get().get_search_key(), 'icon_io_failure', str(source))
                command.execute = io_failure
                with self.assertRaisesRegex(OSError, 'preview IO failure'):
                    Command.execute_cmd(command)
                self.assertEqual(web.read_bytes(), b'old web')
                self.assertEqual(icon.read_bytes(), b'old icon')
                command = Command()
                def checkin_fail():
                    command.get_transaction().set_sync(False)
                    api.simple_checkin(ticket, Project.get().get_search_key(), 'icon_rollback', str(source))
                    raise ValueError('late checkin failure')
                command.execute = checkin_fail
                with self.assertRaisesRegex(ValueError, 'late checkin failure'):
                    Command.execute_cmd(command)
                self.assertEqual(web.read_bytes(), b'old web')
                self.assertEqual(icon.read_bytes(), b'old icon')
                search = Search('sthpw/snapshot')
                search.add_filter('context', 'icon_rollback')
                self.assertEqual(search.get_count(), 0)
