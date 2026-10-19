"""Plain typed projection of legacy FormatMessageWdg; never execute message HTML."""

import json
import math

from tactic.ui.common import BaseTableElementWdg


class MessageTableElementWdg(BaseTableElementWdg):
    def is_editable(self):
        return False

    def get_cell_value(self):
        message = self.get_current_sobject()
        value = str(message.get_value('message', no_exception=True) or '')
        category = message.get_value('category', no_exception=True)
        body, title, progress = value, '', None
        if value.startswith('{') and value.endswith('}'):
            data = json.loads(value)
            if category == 'sobject':
                update = data.get('update_data') or {}
                record = data.get('sobject') or {}
                kind = data.get('search_type')
                if kind == 'sthpw/note':
                    title, body = 'Note added', update.get('note') or ''
                elif kind == 'sthpw/task':
                    title, body = 'Task modified', update.get('process') or ''
                elif kind == 'sthpw/snapshot':
                    title, body = 'Files checked in', record.get('process') or ''
                else:
                    title = 'Object modified'
                    body = '\n'.join(f'{key} – {value}' for key, value in update.items())
                    if not update and data.get('mode') == 'retire':
                        title = 'Retired'
                    if record.get('code'):
                        body = str(record['code']) + ('\n' + body if body else '')
            else:
                body = data.get('message') or data.get('description') or ''
                if category == 'progress':
                    progress = float(data.get('progress') or 0)
                    if not math.isfinite(progress):
                        raise ValueError('Message progress must be finite')
                    progress = max(0, min(100, progress))
        return dict(text=str(body), messageLabel=title,
                    author=str(message.get_value('login', no_exception=True) or ''),
                    progress=progress)

    def get_text_value(self):
        return self.get_cell_value()['text']
