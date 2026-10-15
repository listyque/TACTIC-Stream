"""Addressed check-in and parser checks; every database/file is a private fixture."""
import shutil
import ast
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import test_read_parity as read_tests
from test_checkin import CheckinParity
from pyasm.biz import Project, Snapshot
from pyasm.checkin import FileCheckin, CheckinException, XMPKeywordsParser, FFProbeMetadataParser, ImageMagickMetadataParser, ParserImportError, CheckinMetadataHandler
from pyasm.command import Command
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from PIL import Image
from tactic_stream.server.api import Api
from test_foundation import ROOT, LEGACY


def indexed_checks(store, password='private-test-password'):
    """Construction races must allocate different contexts during execution."""
    barrier = Barrier(2)
    api = Api(store)
    ticket = api.get_ticket('admin', password)
    def publish(index):
        with request_context(RequestContext(store, 'admin', 'admin')):
            api.auth.bind_security('admin', ticket)
            source = store.data_dir / ('concurrent%d.png' % index)
            Image.new('RGB', (31, 17), (index, 40, 60)).save(source)
            command = FileCheckin(Project.get(), [str(source)], context='concurrent/index',
                mode='copy', checkin_type='strict', context_index_padding='2')
            barrier.wait(timeout=10)
            snapshot = Command.execute_cmd(command)
            assert Path(snapshot.get_lib_path_by_type()).read_bytes() == source.read_bytes()
            return snapshot.get_value('context')
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(publish, (1, 2))) == ['concurrent/index/01', 'concurrent/index/02']


class MetadataCheckinParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='metadata_checkin_contract', project='admin', name='metadata_checkin'),
                     dict(method='metadata_checkin_contract', project='admin', name='metadata_hook', hook=True)]

    new_result = CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        if case.get('hook'):
            self.assertEqual(original, {'error': 'AttributeError', 'message': "'NoneType' object has no attribute 'get_lib_dir'"})
            self.assertEqual([row[:3] for row in result[2:5]], [['metadata_checkin/001', 1, 'metadata_checkin/001'], ['metadata_checkin/002', 1, 'metadata_checkin/002'], ['metadata_checkin/003', 1, 'metadata_checkin/003']])
            self.assertEqual(result[2][3]['width'], 31)
        else:
            self.assertEqual(result, original)

    def test_index_allocation_and_failed_parser_roll_back(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            indexed_checks(store)
            with store.connection(write=True) as db:
                db.execute("UPDATE search_object SET metadata_parser='PIL' WHERE search_type='sthpw/project'")
            with request_context(RequestContext(store, 'admin', 'admin')):
                Api(store).auth.bind_security('admin', self.ticket)
                source = Path(directory) / 'failure.png'
                Image.new('RGB', (31, 17)).save(source)
                parent = Project.get()
                for width in (-1, 33, True, 1.5, 'invalid', '0'):
                    with self.assertRaises(CheckinException):
                        FileCheckin(parent, [str(source)], context_index_padding=width)
                # Width is a minimum, and nested contexts must inspect the whole suffix.
                naming = dict(dir_naming='admin/metadata/{snapshot.context}')
                Command.execute_cmd(FileCheckin(parent, [str(source)], context='nested/path/99', mode='copy', checkin_type='strict', **naming))
                snapshot = Command.execute_cmd(FileCheckin(parent, [str(source)], context='nested/path', context_index_padding=2, mode='copy', checkin_type='strict', **naming))
                self.assertEqual(snapshot.get_value('context'), 'nested/path/100')
                snapshot = Command.execute_cmd(FileCheckin(parent, [str(source)], context='nested/path', context_index_padding=2, mode='copy', checkin_type='strict', **naming))
                self.assertEqual(snapshot.get_value('context'), 'nested/path/101')
                before = [Search(kind).get_count() for kind in ('sthpw/snapshot', 'sthpw/file')]
                payload = source.read_bytes()
                command = FileCheckin(parent, [str(source)], context='failed/index', context_index_padding=2, mode='copy', checkin_type='strict')
                with patch.object(CheckinMetadataHandler, 'execute', side_effect=ValueError('parser failed')):
                    with self.assertRaisesRegex(ValueError, 'parser failed'):
                        Command.execute_cmd(command)
                self.assertEqual([Search(kind).get_count() for kind in ('sthpw/snapshot', 'sthpw/file')], before)
                self.assertEqual(source.read_bytes(), payload)
                snapshot = Command.execute_cmd(FileCheckin(parent, [str(source)], context='failed/index', context_index_padding=2, mode='copy', checkin_type='strict'))
                self.assertEqual(snapshot.get_value('context'), 'failed/index/01')

    def test_xmp_and_external_parser_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'keywords.bin'
            path.write_bytes(b'prefix<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/"><rdf:RDF><rdf:Description><dc:subject><rdf:Bag><rdf:li>First</rdf:li><rdf:li>Second</rdf:li></rdf:Bag></dc:subject></rdf:Description></rdf:RDF></x:xmpmeta>suffix')
            parser = XMPKeywordsParser(path=str(path))
            self.assertTrue(parser.check_xmpmetadata())
            self.assertEqual(parser.get_metadata(), {'keywords': 'first second'})
            path.write_bytes(b'<x:xmpmeta>incomplete')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                parser.get_metadata()
            path.write_bytes(b'no XMP')
            self.assertEqual(parser.get_metadata(), {'keywords': ''})
        parser = FFProbeMetadataParser(path='video.mov')
        self.assertEqual(parser.parse_output(b'codec_type=video\ncodec_name=a=b\n'), {'video:codec_type': 'video', 'video:codec_name': 'a=b'})
        with patch('pyasm.checkin.metadata.HAS_FFMPEG', False), self.assertRaises(ParserImportError):
            parser.get_metadata()
        for parser, flag in ((parser, 'HAS_FFMPEG'), (ImageMagickMetadataParser(path='image.png'), 'HAS_IMAGEMAGICK')):
            with patch('pyasm.checkin.metadata.' + flag, True), patch('pyasm.checkin.metadata.subprocess.run', side_effect=subprocess.TimeoutExpired('tool', 30)) as run:
                with self.assertRaises(subprocess.TimeoutExpired):
                    parser.get_metadata()
                self.assertEqual(run.call_args.kwargs['timeout'], 30)
                self.assertTrue(run.call_args.kwargs['check'])

    def test_public_metadata_signatures_auto_selection_and_upgrade(self):
        import pyasm.checkin as checkin
        import pyasm.checkin.metadata as metadata
        def signatures(path):
            return {node.name: {method.name: ast.dump(method.args) for method in node.body if isinstance(method, ast.FunctionDef)}
                    for node in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(node, ast.ClassDef)}
        original = signatures(LEGACY / 'src/pyasm/checkin/metadata.py')
        native = signatures(ROOT / 'src/pyasm/checkin/metadata.py')
        for name in metadata.__all__:
            self.assertIs(getattr(checkin, name), getattr(metadata, name))
            self.assertEqual(native[name], original[name], name)
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with store.connection(write=True) as db:
                db.execute('ALTER TABLE search_object DROP COLUMN metadata_parser')
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with request_context(RequestContext(store, 'admin', 'admin')):
                from pyasm.biz import File
                image = Path(directory) / 'image.png'
                text = Path(directory) / 'normal.txt'
                Image.new('RGB', (31, 17)).save(image)
                text.write_text('normal')
                files = [File.create_new(), File.create_new()]
                for file in files:
                    file.set_value('checkin_dir', directory)
                snapshot = Snapshot.create_new()
                with patch('pyasm.checkin.metadata.HAS_IMAGEMAGICK', False):
                    CheckinMetadataHandler(snapshot=snapshot, files=[str(image), str(text)], file_objects=files, parser='auto', commit=False).execute()
                self.assertEqual(files[0].get_metadata()['width'], 31)
                self.assertEqual(snapshot.get_metadata()['__parser__'], 'PIL')
                self.assertFalse(files[1].get_value('metadata'))
