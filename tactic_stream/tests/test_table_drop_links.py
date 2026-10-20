"""Configured drop links preserve instance scope, revisions and atomic replacement."""
import unittest

import test_table_services as services_fixture
from test_table_embedded_widgets import write
from pyasm.search import Search
from tactic.ui.table.drop_element_wdg import DropElementWdg, DropElementEditCmd, edit_drop_links


class TableDropLinks(unittest.TestCase):
    setUp = services_fixture.TableServices.setUp

    def members(self):
        with self.store.connection() as database:
            return sorted(tuple(row) for row in database.execute("SELECT login,login_group FROM login_in_group WHERE login_group='crew'"))

    def prepare(self):
        with self.store.connection(write=True) as database:
            database.execute("INSERT INTO login_group(code,login_group,description) VALUES('crew','crew','Crew')")
            database.execute("INSERT INTO login(code,login,display_name,password) VALUES('artist','artist','Artist','disabled')")
            database.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('crew-admin','admin','crew')")
        group = Search.get_by_code('sthpw/login_group','crew')
        widget = DropElementWdg(name='users',instance_type='sthpw/login_in_group',accepted_drop_type='sthpw/login')
        widget.set_sobject(group)
        cell = widget.get_cell_value()
        args = dict(search_type='sthpw/login_group',view='table',column='users',parent_key=group.get_search_key())
        prepared = edit_drop_links(**args)
        return group,cell,args,prepared

    def test_real_membership_projection_and_replacement(self):
        group,cell,args,prepared=self.prepare()
        self.assertTrue(cell['available'])
        self.assertEqual(len(cell['links']),1)
        self.assertEqual(cell['links'][0]['record']['code'],'admin')
        self.assertNotIn('password',cell['links'][0]['record'])
        self.assertEqual(cell['expectedRevision'],prepared['expected_revision'])
        artist=Search.get_by_code('sthpw/login','artist').get_search_key()
        result=write(lambda:DropElementEditCmd(**args,action='save',target_keys=[artist],expected_revision=prepared['expected_revision']).execute())
        self.assertEqual(result['state'],'saved')
        self.assertEqual(self.members(),[('artist','crew')])
        self.assertEqual(edit_drop_links(**args,action='check',target_keys=[artist],expected_revision=prepared['expected_revision'])['state'],'saved')

    def test_stale_revision_and_wrong_type_never_delete_current_links(self):
        group,cell,args,prepared=self.prepare()
        with self.store.connection(write=True) as database:
            database.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('crew-artist','artist','crew')")
        with self.assertRaisesRegex(ValueError,'changed'):
            write(lambda:DropElementEditCmd(**args,action='save',target_keys=[],expected_revision=prepared['expected_revision']).execute())
        self.assertEqual(self.members(),[('admin','crew'),('artist','crew')])
        fresh=edit_drop_links(**args)
        with self.assertRaisesRegex(ValueError,'another Search Type'):
            write(lambda:DropElementEditCmd(**args,action='save',target_keys=[group.get_search_key()],expected_revision=fresh['expected_revision']).execute())
        self.assertEqual(self.members(),[('admin','crew'),('artist','crew')])

    def test_database_failure_after_removal_rolls_back_all_instance_changes(self):
        group,cell,args,prepared=self.prepare()
        with self.store.connection(write=True) as database:
            database.execute("CREATE TRIGGER reject_drop_fixture BEFORE INSERT ON login_in_group WHEN NEW.login='artist' BEGIN SELECT RAISE(ABORT,'reject fixture'); END")
        artist=Search.get_by_code('sthpw/login','artist').get_search_key()
        with self.assertRaisesRegex(Exception,'reject fixture'):
            write(lambda:DropElementEditCmd(**args,action='save',target_keys=[artist],expected_revision=prepared['expected_revision']).execute())
        self.assertEqual(self.members(),[('admin','crew')])


if __name__=='__main__':
    unittest.main()
