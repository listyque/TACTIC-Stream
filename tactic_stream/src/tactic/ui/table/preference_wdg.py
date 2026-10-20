"""Descriptions and help hints from the original server preference table."""
from tactic.ui.common import BaseTableElementWdg
from pyasm.biz import PrefSetting
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search
import hashlib
import json


def preference_revision(key):
    record = PrefSetting.get_by_key(key, use_cache=False)
    return hashlib.sha256(json.dumps(record.get_data() if record else None,
                                    sort_keys=True, default=str).encode()).hexdigest()


class PreferenceEditWdg(BaseTableElementWdg):
    def get_cell_value(self):
        obj = self.get_current_sobject()
        key = obj.get_value('key')
        record = PrefSetting.get_by_key(key, use_cache=False)
        value = record.get_value('value') if record else ''
        choices = str(obj.get_value('options') or '').split('|') if obj.get_value('type') == 'sequence' else []
        return dict(text=value, preferenceKey=key, targetSearchKey=obj.get_search_key(), expectedRevision=preference_revision(key),
                    preferenceOptions=[dict(value=item, label=item) for item in choices], actions=[
                        dict(name='preference', label='Edit preference', icon='edit')])


class SetPreferenceCmd(Command):
    """Original current-user preference command, with optional stale-write guard."""

    def execute(self):
        key, value = self.kwargs.get('key'), self.kwargs.get('value')
        action = self.kwargs.get('action', 'save')
        if not isinstance(key, str) or not key or not isinstance(value, str):
            raise ValueError('Invalid preference')
        if action not in ('save', 'check'):
            raise ValueError('Invalid preference operation')
        if not Environment.get_user_name() or Environment.get_user_name() == 'anonymous':
            raise PermissionError('Sign in before changing preferences')
        expected = self.kwargs.get('expected_revision')
        if action == 'check':
            record = PrefSetting.get_by_key(key, use_cache=False)
            current = record.get_value('value') if record else ''
            return dict(state='saved' if current == value else 'unchanged' if expected == preference_revision(key) else 'conflict')
        sql = Search('sthpw/pref_setting').get_sql()
        sql.get_database_impl().lock_collection_table(sql, 'pref_setting')
        if expected is not None and expected != preference_revision(key):
            raise ValueError('Preference changed. Reload before saving.')
        PrefSetting.create(key, value)
        return dict(state='saved')


class PreferenceDescriptionWdg(BaseTableElementWdg):
    def get_cell_value(self):
        obj = self.get_current_sobject()
        hints = {
            'Debug': 'If set to [true], you can view the Debug Widget at the bottom left corner of your page.',
            'Filter': 'If set to [multi], It generally applies to filters in the filter box for Artist Tab.',
            'Quick Text': 'A list of | separated phrases a user can pick from to enter into the note area of Note Sheet.'
        }
        return {'text': obj.get_description(), 'tooltip': hints.get(obj.get_value('title'), '')}
