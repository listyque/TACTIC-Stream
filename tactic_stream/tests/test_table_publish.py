"""Configured publish cells keep the existing form and its actual actions."""
import unittest

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.search import Search, SearchType
from tactic_stream.server.interface import read_form, read_interface
from tactic_stream.server.table_cells import read_table_cells


class TablePublish(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def configure(self, element, view='publish_table_test'):
        config = SearchType.create('config/widget_config')
        config.set_value('search_type', 'contract/entity')
        config.set_value('view', view)
        config.set_value('config', '<config><' + view + '>' + element + '</' + view + '></config>')
        write(config.commit)

    def test_both_canonical_publish_types_keep_the_configured_form_and_preview(self):
        from pyasm.widget import PublishTableElement
        from tactic.ui.table import GeneralPublishElementWdg
        key = 'contract/entity?project=one&code=A'
        self.configure('<element name="publish"><display class="PublishTableElement"/></element>'
            '<element name="general"><display class="tactic.ui.table.GeneralPublishElementWdg">'
            '<view>review_publish</view><preview>false</preview></display></element>')
        description = read_interface('contract/entity', 'publish_table_test')['table']['elements']
        self.assertTrue(all(item['cell']['supported'] for item in description))
        cells = read_table_cells('contract/entity', 'publish_table_test', [key])[key]
        self.assertEqual(cells['publish']['publishView'], 'publish')
        self.assertEqual(cells['general']['publishView'], 'review_publish')
        self.assertNotIn('preview', cells['general'])
        self.assertEqual(cells['publish']['targetSearchKey'], key)
        self.assertEqual(cells['publish']['projectCode'], 'one')
        widget = GeneralPublishElementWdg(name='general')
        widget.set_sobjects([Search.get_by_search_key(key)])
        widget.preprocess()
        self.assertIn('preview', widget.get_cell_value())
        self.assertTrue(issubclass(GeneralPublishElementWdg, PublishTableElement))

    def test_unknown_view_and_options_remain_explicit(self):
        from tactic.ui.table import GeneralPublishElementWdg
        widget = GeneralPublishElementWdg(name='general', view='../not_a_view', preview='false')
        widget.set_sobjects([Search.get_by_code('contract/entity', 'A')])
        with self.assertRaisesRegex(ValueError, 'Invalid publish view'):
            widget.get_cell_value()
        self.configure('<element name="publish"><display class="PublishTableElement">'
            '<invented_option>true</invented_option></display></element>')
        column = read_interface('contract/entity', 'publish_table_test')['table']['elements'][0]
        self.assertFalse(column['cell']['supported'])

    def test_publish_view_preserves_its_fields_actions_and_existing_record(self):
        self.configure('<element name="name"><display class="pyasm.widget.TextWdg"/></element>'
            '<element name="attachment"><display class="tactic.ui.widget.SimpleUploadWdg">'
            '<context>publish/reference</context></display><action class="pyasm.command.UploadAction"/></element>', 'review_publish')
        definition = read_form('contract/entity', view='review_publish', search_key='contract/entity?project=one&code=A')
        self.assertEqual(definition['mode'], 'edit')
        self.assertEqual([field['name'] for field in definition['fields']], ['name', 'attachment'])
        attachment = definition['fields'][1]
        self.assertEqual(attachment['action']['handler'], 'pyasm.command.UploadAction')
        self.assertEqual(attachment['input']['context'], 'publish/reference')
        self.assertEqual(definition['fields'][0]['values'], ['Первый'])

    def test_actual_publish_form_uploads_with_its_action_and_rolls_back_late_failure(self):
        from pathlib import Path
        from unittest.mock import patch
        from pyasm.command import Command, UploadAction
        from pyasm.common import Environment
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        with self.store.connection('one', write=True) as database:
            database.execute('ALTER TABLE entity ADD COLUMN attachment text')
        self.configure('<element name="name"><display class="pyasm.widget.TextWdg"/></element>'
            '<element name="attachment"><display class="tactic.ui.widget.SimpleUploadWdg">'
            '<context>publish/reference</context></display><action class="pyasm.command.UploadAction"/></element>', 'review_publish')
        key = 'contract/entity?project=one&code=A'
        definition = read_form('contract/entity', view='review_publish', search_key=key)
        upload = Path(Environment.get_upload_dir()) / 'table-publish.txt'
        upload.parent.mkdir(parents=True, exist_ok=True)
        payload = b'configured publish bytes\x00'
        original = UploadAction.postprocess
        def save(fail):
            upload.write_bytes(payload)
            for name, value in {'name':'Published name', 'attachment|path':'/client/table-publish.txt',
                    'attachment|ticket':Environment.get_ticket(), 'attachment|context':'publish/reference'}.items():
                WebContainer.get_web().set_form_value(definition['input_prefix'] + '|' + name, value)
            cmd = EditCmd(search_key=key, view='review_publish', element_names=['name','attachment'], input_prefix=definition['input_prefix'])
            def postprocess(action):
                original(action)
                if fail:
                    raise ValueError('Late configured publish failure')
            with patch.object(UploadAction, 'postprocess', postprocess):
                Command.execute_cmd(cmd)
        with self.assertRaisesRegex(ValueError, 'Late configured publish failure'):
            save(True)
        self.assertEqual(Search.get_by_search_key(key).get_value('name'), 'Первый')
        search = Search('sthpw/snapshot')
        search.add_filter('context', 'publish/reference')
        search.add_filter('version', 0, '>')
        self.assertEqual(search.get_count(), 0)
        save(False)
        snapshots = search.get_sobjects()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].get_value('search_code'), 'A')
        file = next(file for file in snapshots[0].get_all_file_objects() if file.get_type() == 'main')
        self.assertEqual(Path(file.get_lib_path()).read_bytes(), payload)
        obj = Search.get_by_search_key(key)
        self.assertEqual(obj.get_value('name'), 'Published name')
        self.assertEqual(obj.get_value('amount'), 0)

    def test_shipped_publish_widgets_support_thumb_and_multi_upload_with_null_action(self):
        import base64
        from pathlib import Path
        from pyasm.command import Command
        from pyasm.common import Environment
        from pyasm.web import WebContainer
        from tactic.ui.panel import EditCmd
        self.configure('<element name="images"><display class="ThumbInputWdg"/></element>'
            '<element name="files"><display class="tactic.ui.widget.UploadWdg">'
            '<names>icon|main</names><required>false|true</required><context_option>publish/asset</context_option>'
            '</display><action class="NullAction"/></element>', 'shipped_publish')
        key = 'contract/entity?project=one&code=B'
        definition = read_form('contract/entity', view='shipped_publish', search_key=key)
        self.assertEqual(definition['fields'][0]['input']['type'], 'thumbnail')
        self.assertTrue(definition['fields'][0]['input']['read_only'])
        upload_field = definition['fields'][1]
        self.assertEqual(upload_field['action']['handler'], 'NullAction')
        self.assertEqual(upload_field['input']['fields'], [
            dict(name='icon', required=False),
            dict(name='main', required=True),
        ])
        upload_dir = Path(Environment.get_upload_dir())
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / 'icon.png').write_bytes(base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='
        ))
        (upload_dir / 'model.ma').write_bytes(b'model-bytes')
        web = WebContainer.get_web()
        prefix = definition['input_prefix']
        for name, value in {
            f'{prefix}|files|context': 'publish/asset',
            f'{prefix}|icon|path': '/client/icon.png',
            f'{prefix}|main|path': '/client/model.ma',
        }.items():
            web.set_form_value(name, value)
        cmd = EditCmd(search_key=key, view='shipped_publish', element_names=['images', 'files'], input_prefix=prefix)
        Command.execute_cmd(cmd)
        search = Search('sthpw/snapshot')
        search.add_filter('search_code', 'B')
        search.add_filter('context', 'publish/asset')
        search.add_filter('version', 0, '>')
        snapshots = search.get_sobjects()
        self.assertEqual(len(snapshots), 1)
        by_type = {f.get_type(): Path(f.get_lib_path()).read_bytes() for f in snapshots[0].get_all_file_objects()}
        self.assertIn('icon', by_type)
        self.assertEqual(by_type['main'], b'model-bytes')
