"""ChatCmd moved from tactic.ui.app.message_wdg into server-side code.

Same message/subscription storage and welcome message as upstream. Fixes:
exact participant-set matching (not any overlapping recipient), current
project on new rows, and input validation. Existing projectless chats remain
available only to their existing participants. No email is sent here.
"""
from pyasm.common import Common, Environment, UserException
from pyasm.search import Search, SearchType
from pyasm.command import Command
from pyasm.biz import Project
from .messaging import in_project, add_project_scope


class ChatCmd(Command):
    def execute(self):
        login = Environment.get_user_name()
        users = self.kwargs.get('users')
        if not isinstance(users, (list, tuple)) or not 1 <= len(users) <= 30:
            raise UserException('Выберите от 1 до 30 участников')
        if any(not isinstance(u, str) or not u.strip() or len(u) > 256 or any(ord(c) < 32 for c in u) for u in users):
            raise UserException('Некорректный login участника')
        users = list(dict.fromkeys(u.strip() for u in users if u.strip() != login))
        if not users:
            raise UserException('Нужен хотя бы один другой участник')
        everyone = {login, *users}
        project = Project.get_project_code()
        available = Search('sthpw/login'); available.add_filters('login', sorted(everyone))
        found = {o.get_value('login') for o in available.get_sobjects()}
        if found != everyone:
            raise UserException('Один из участников отсутствует или архивирован')
        mine = Search('sthpw/subscription'); mine.add_filter('login', login)
        mine.add_filter('category', 'chat'); add_project_scope(mine, project)
        mine.add_order_by('id', direction='desc'); mine.set_limit(2001)
        own = mine.get_sobjects()
        if len(own) > 2000:
            raise UserException('Более 2000 чатов: требуется отдельный поиск существующей переписки')
        keys = sorted({o.get_value('message_code') for o in own if o.get_value('message_code')})
        # Batch participants instead of one query per recipient and conversation.
        participants, messages = {}, {}
        for offset in range(0, len(keys), 200):
            group = keys[offset:offset+200]
            qs = Search('sthpw/subscription'); qs.add_filters('message_code', group)
            qs.set_limit(10001)
            rows = qs.get_sobjects()
            if len(rows) > 10000:
                raise UserException('Слишком много участников для безопасного сопоставления чатов')
            for row in rows:
                participants.setdefault(row.get_value('message_code'), []).append(row)
            qm = Search('sthpw/message'); qm.add_filters('code', group)
            messages.update({o.get_code(): o for o in qm.get_sobjects()})
        for row in own:
            key = row.get_value('message_code'); message = messages.get(key)
            peers = participants.get(key, [])
            if not message or message.get_value('category') != 'chat' or not in_project(message.get_value('project_code', no_exception=True), project):
                continue
            if any(p.get_value('category') != 'chat' or not in_project(p.get_value('project_code', no_exception=True), project) for p in peers):
                continue
            if {p.get_value('login') for p in peers} == everyone and len(peers) == len(everyone):
                self.info.update(message_code=key, created=False)
                return
        key = Common.generate_random_key()
        message = SearchType.create('sthpw/message')
        for name, value in {'code':key, 'login':login, 'category':'chat', 'message':'Welcome!!!', 'project_code':project}.items():
            message.set_value(name, value)
        message.commit()
        for person in sorted(everyone):
            subscription = SearchType.create('sthpw/subscription')
            for name, value in {'message_code':key, 'login':person, 'category':'chat', 'project_code':project}.items():
                subscription.set_value(name, value)
            subscription.commit()
        self.info.update(message_code=key, created=True)
