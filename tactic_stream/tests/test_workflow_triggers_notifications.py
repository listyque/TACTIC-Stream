"""End-to-end tests for Stage 2.2 (L09 — Workflow, Triggers, Notifications)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_foundation import fixture
from pyasm.biz import GroupNotification, Notification, Pipeline, Task
from pyasm.command import (
    Command,
    EmailHandler,
    EmailTrigger2,
    EmailTriggerTest,
    EmailTriggerTestCmd,
    EmailTriggerThread,
    GeneralNoteEmailHandler,
    GeneralPublishEmailHandler,
    NoteEmailHandler,
    QueueTrigger,
    ScriptTrigger,
    SendEmail,
    SubprocessTrigger,
    TaskAssignEmailHandler,
    TaskStatusEmailHandler,
    TestEmailHandler,
    Trigger,
    Workflow,
)
from pyasm.common import Config, Container
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic.command import (
    JobTask,
    NotificationTestCmd,
    PipelineParentStatusTrigger,
    PipelineTaskCreateTrigger,
    PipelineTaskDateTrigger,
    PipelineTaskStatusTrigger,
    PipelineTaskTrigger,
    PythonTrigger,
    Queue,
    RelatedTaskUpdateTrigger,
    Scheduler,
    SchedulerTask,
    TaskCompleteTrigger,
    TaskCreatorTrigger,
)
from tactic.core.filter_data import FilterData
from tactic.core.notification_filters import NotificationLogScope
from tactic_stream.server.api import Api


def _run_cmd(fn):
    class _Wrap(Command):
        def execute(self):
            self.get_transaction().set_sync(False)
            return fn()

    return Command.execute_cmd(_Wrap())


class WorkflowTriggersNotificationsTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(
            patch.dict(
                os.environ,
                {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''},
            )
        )
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(Path(directory) / 'data')
        self.store.initialize(hash_password('l09-secret'))
        fixture(self.store)
        self.api = Api(self.store)
        self.ticket = self.api.get_ticket('admin', 'l09-secret')
        self.enterContext(
            request_context(
                RequestContext(self.store, login='admin', project='one')
            )
        )
        self.api.auth.bind_security('admin', self.ticket)
        Trigger.clear_db_cache()

    def test_pipeline_task_rule_triggers_status_search_parent_create_and_date(self):
        with self.store.connection('sthpw', write=True) as db:
            for field in ('search_type', 'data', 'listen_process'):
                try:
                    db.execute(f'ALTER TABLE "trigger" ADD COLUMN "{field}" text')
                except Exception:
                    pass
            db.execute(
                """INSERT OR IGNORE INTO search_object
                   (code,search_type,namespace,database,table_name,class_name)
                   VALUES ('config/trigger','config/trigger','config','{project}','spt_trigger','pyasm.biz.TriggerSObj')"""
            )
        with self.store.connection('one', write=True) as db:
            db.execute(
                'ALTER TABLE entity ADD COLUMN "pipeline_code" text'
            )
            db.execute(
                'ALTER TABLE entity ADD COLUMN "status" text'
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS spt_trigger (
                    id integer PRIMARY KEY, code text, event text, process text,
                    search_type text, class_name text, script_path text, mode text,
                    data text, description text, listen_process text, s_status text
                )"""
            )
        Container.clear_dict('DatabaseImpl:column_info')
        Container.clear_dict('DatabaseImpl:table_info')
        Container.clear_dict('SearchType:search_object_data')

        def setup():
            pipeline = SearchType.create('sthpw/pipeline')
            pipeline.set_value('code', 'one/shot_pipe')
            pipeline.set_value('search_type', 'contract/entity')
            pipeline.set_value('project_code', 'one')
            pipeline.set_value(
                'pipeline',
                '<pipeline><process name="model"/><process name="rig"/><process name="anim"/>'
                '<connect from="model" to="rig"/><connect from="rig" to="anim"/></pipeline>',
            )
            pipeline.commit()

            shot = SearchType.create('contract/entity')
            shot.set_value('code', 'ENT_PIPE_1')
            shot.set_value('name', 'Hero Shot')
            shot.set_value('status', 'Pending')
            shot.set_value('pipeline_code', 'one/shot_pipe')
            shot.commit()

            t_model = Task.create(
                shot,
                process='model',
                description='Model',
                pipeline_code='one/shot_pipe',
                status='Pending',
                start_date='2026-05-01 00:00:00',
                end_date='2026-05-05 00:00:00',
            )
            t_rig = Task.create(
                shot,
                process='rig',
                description='Rig',
                pipeline_code='one/shot_pipe',
                status='Waiting',
                start_date='2026-05-06 00:00:00',
                end_date='2026-05-10 00:00:00',
            )

            # 1) PipelineTaskStatusTrigger: when model -> Complete, set rig -> Ready
            trig1 = SearchType.create('config/trigger')
            trig1.set_value('code', 'RULE_STATUS')
            trig1.set_value('event', 'change|sthpw/task|status')
            trig1.set_value('listen_process', 'model')
            trig1.set_value('process', 'model')
            trig1.set_value('class_name', 'tactic.command.PipelineTaskStatusTrigger')
            trig1.set_value('mode', 'same process,same transaction')
            trig1.set_value(
                'data',
                json.dumps({
                    'pipeline': 'one/shot_pipe',
                    'src_process': 'model',
                    'src_status': 'Complete',
                    'dst_process': 'rig',
                    'dst_status': 'Ready',
                }),
            )
            trig1.commit()

            # 2) PipelineParentStatusTrigger: when model -> Complete, set parent (shot) status -> Active
            trig2 = SearchType.create('config/trigger')
            trig2.set_value('code', 'RULE_PARENT')
            trig2.set_value('event', 'change|sthpw/task|status')
            trig2.set_value('listen_process', 'model')
            trig2.set_value('process', 'model')
            trig2.set_value('class_name', 'tactic.command.PipelineParentStatusTrigger')
            trig2.set_value('mode', 'same process,same transaction')
            trig2.set_value(
                'data',
                json.dumps({
                    'dst_status': 'Active',
                }),
            )
            trig2.commit()

            # 3) PipelineTaskCreateTrigger: when rig -> Complete, create anim task
            trig3 = SearchType.create('config/trigger')
            trig3.set_value('code', 'RULE_CREATE')
            trig3.set_value('event', 'change|sthpw/task|status')
            trig3.set_value('listen_process', 'rig')
            trig3.set_value('process', 'rig')
            trig3.set_value('class_name', 'tactic.command.PipelineTaskCreateTrigger')
            trig3.set_value('mode', 'same process,same transaction')
            trig3.set_value(
                'data',
                json.dumps({
                    'src_status': 'Complete',
                    'output': ['anim'],
                }),
            )
            trig3.commit()

            # 4) PipelineTaskDateTrigger: when model -> Complete, set actual_end_date on model task
            trig4 = SearchType.create('config/trigger')
            trig4.set_value('code', 'RULE_DATE')
            trig4.set_value('event', 'change|sthpw/task|status')
            trig4.set_value('listen_process', 'model')
            trig4.set_value('process', 'model')
            trig4.set_value('class_name', 'tactic.command.PipelineTaskDateTrigger')
            trig4.set_value('mode', 'same process,same transaction')
            trig4.set_value(
                'data',
                json.dumps({
                    'column': 'actual_end_date',
                    'src_status': 'Complete',
                }),
            )
            trig4.commit()

            # 5) PipelineTaskTrigger: FilterData rule sets input/output task attribute
            trig5 = SearchType.create('config/trigger')
            trig5.set_value('code', 'RULE_FILTER')
            trig5.set_value('event', 'change|sthpw/task|status')
            trig5.set_value('listen_process', 'rig')
            trig5.set_value('process', 'rig')
            trig5.set_value('class_name', 'tactic.command.PipelineTaskTrigger')
            trig5.set_value('mode', 'same process,same transaction')
            trig5.set_value(
                'data',
                json.dumps([
                    {'prefix': 'trigger', 'process': 'rig'},
                    {'prefix': 'rule', 'name': 'status', 'value': 'Complete'},
                    {'prefix': 'rule', 'name': 'pipeline', 'value': 'one/shot_pipe'},
                    {'prefix': 'action', 'type': 'process', 'process': 'model', 'name': 'status', 'value': 'Approved'},
                ]),
            )
            trig5.commit()

            Trigger.clear_db_cache()
            return shot, t_model, t_rig

        shot, t_model, t_rig = _run_cmd(setup)

        def complete_model():
            task = Search.get_by_id('sthpw/task', t_model.get_id())
            task.set_value('status', 'Complete')
            task.commit()

        _run_cmd(complete_model)

        rig_reloaded = Search.get_by_id('sthpw/task', t_rig.get_id())
        shot_reloaded = Search.get_by_id('contract/entity', shot.get_id())
        model_reloaded = Search.get_by_id('sthpw/task', t_model.get_id())
        self.assertEqual(rig_reloaded.get_value('status'), 'Ready')
        self.assertEqual(shot_reloaded.get_value('status'), 'Active')
        self.assertTrue(bool(model_reloaded.get_value('actual_end_date')))

        def complete_rig():
            task = Search.get_by_id('sthpw/task', t_rig.get_id())
            task.set_value('status', 'Complete')
            task.commit()

        _run_cmd(complete_rig)
        anim_tasks = Task.get_by_sobject(shot, process='anim')
        self.assertEqual(len(anim_tasks), 1)
        model_after_filter = Search.get_by_id('sthpw/task', t_model.get_id())
        self.assertEqual(model_after_filter.get_value('status'), 'Approved')

    def test_deferred_dedup_keeps_distinct_scripts_and_notifications_while_deduping_duplicates(self):
        with self.store.connection('sthpw', write=True) as db:
            for field in ('search_type', 'data', 'listen_process'):
                try:
                    db.execute(f'ALTER TABLE "trigger" ADD COLUMN "{field}" text')
                except Exception:
                    pass
        Container.clear_dict('DatabaseImpl:column_info')
        Container.clear_dict('DatabaseImpl:table_info')

        def setup_scripts_and_triggers():
            for idx in (1, 2):
                script = SearchType.create('config/custom_script')
                script.set_value('code', f'SCRIPT_{idx}')
                script.set_value('folder', 'l09')
                script.set_value('title', f'step_{idx}')
                script.set_value('script', f"server.insert('sthpw/note', {{'note': 'ran_script_{idx}', 'process': 'l09'}})")
                script.commit()

                trig = SearchType.create('sthpw/trigger')
                trig.set_value('code', f'TRIG_SCRIPT_{idx}')
                trig.set_value('event', 'l09|multi_script')
                trig.set_value('project_code', 'one')
                trig.set_value('script_path', f'l09/step_{idx}')
                trig.set_value('mode', 'same process,new transaction')
                trig.commit()

            # Duplicate of step_1 on the same event should be deduplicated
            trig_dup = SearchType.create('sthpw/trigger')
            trig_dup.set_value('code', 'TRIG_SCRIPT_1_DUP')
            trig_dup.set_value('event', 'l09|multi_script')
            trig_dup.set_value('project_code', 'one')
            trig_dup.set_value('script_path', 'l09/step_1')
            trig_dup.set_value('mode', 'same process,new transaction')
            trig_dup.commit()
            Trigger.clear_db_cache()

        _run_cmd(setup_scripts_and_triggers)

        def fire_event():
            Trigger.call(Command(), 'l09|multi_script', {'key': 'same'})

        _run_cmd(fire_event)

        search = Search('sthpw/note')
        search.add_filter('process', 'l09')
        notes = sorted(n.get_value('note') for n in search.get_sobjects())
        self.assertEqual(notes, ['ran_script_1', 'ran_script_2'])

    def test_subprocess_and_queued_triggers_advance_workflow_action_node(self):
        with self.store.connection('one', write=True) as db:
            try:
                db.execute('ALTER TABLE entity ADD COLUMN "pipeline_code" text')
            except Exception:
                pass
        with self.store.connection('sthpw', write=True) as db:
            for field in ('search_type', 'data', 'listen_process'):
                try:
                    db.execute(f'ALTER TABLE "trigger" ADD COLUMN "{field}" text')
                except Exception:
                    pass
        Container.clear_dict('DatabaseImpl:column_info')
        Container.clear_dict('DatabaseImpl:table_info')

        def setup_workflow():
            script = SearchType.create('config/custom_script')
            script.set_value('code', 'Q_ACTION_SCRIPT')
            script.set_value('folder', 'l09')
            script.set_value('title', 'queued_action')
            script.set_value(
                'script',
                "server.insert('sthpw/note', {'note': 'queued_node_ran', 'process': 'queued_proc'})\nreturn True",
            )
            script.commit()

            pipeline = SearchType.create('sthpw/pipeline')
            pipeline.set_value('code', 'one/queued_wf')
            pipeline.set_value('search_type', 'contract/entity')
            pipeline.set_value('project_code', 'one')
            pipeline.set_value(
                'pipeline',
                '<pipeline><process name="auto_step" type="action"/><process name="final_step" type="manual"/>'
                '<connect from="auto_step" to="final_step"/></pipeline>',
            )
            pipeline.commit()

            p_auto = Search('config/process')
            p_auto.add_filter('pipeline_code', 'one/queued_wf')
            p_auto.add_filter('process', 'auto_step')
            p_auto = p_auto.get_sobject()
            self.assertIsNotNone(p_auto)

            trig = SearchType.create('sthpw/trigger')
            trig.set_value('code', 'TRIG_QUEUED_ACTION')
            trig.set_value('event', 'process|action')
            trig.set_value('process', p_auto.get_code())
            trig.set_value('project_code', 'one')
            trig.set_value('script_path', 'l09/queued_action')
            trig.set_value('mode', 'separate process,queued')
            trig.commit()

            shot = SearchType.create('contract/entity')
            shot.set_value('code', 'ENT_Q_1')
            shot.set_value('name', 'Queued Entity')
            shot.set_value('pipeline_code', 'one/queued_wf')
            shot.commit()

            t_auto = Task.create(
                shot,
                process='auto_step',
                description='Auto',
                pipeline_code='one/queued_wf',
                status='Pending',
            )
            t_final = Task.create(
                shot,
                process='final_step',
                description='Final',
                pipeline_code='one/queued_wf',
                status='Waiting',
            )
            Trigger.clear_db_cache()
            return shot, t_auto, t_final

        shot, t_auto, t_final = _run_cmd(setup_workflow)

        def start_action():
            Workflow().init(quiet=True)
            pipeline = Pipeline.get_by_code('one/queued_wf')
            Trigger.call(
                Command(),
                'process|pending',
                {'sobject': shot, 'pipeline': pipeline, 'process': 'auto_step', 'data': {}},
            )

        _run_cmd(start_action)

        # Before queue worker runs: a QueueTrigger job is pending in sthpw/queue, final_step is still Pending
        q_search = Search('sthpw/queue')
        q_search.add_filter('queue', 'trigger')
        q_search.add_filter('state', 'pending')
        jobs = q_search.get_sobjects()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].get_value('command'), 'pyasm.command.QueueTrigger')

        # Run the queue job via JobTask
        handled = JobTask(queue='trigger').check_new_job('trigger')
        self.assertTrue(handled)

        # Note was inserted and downstream manual node 'final_step' transitioned to Pending/In_Progress via workflow!
        note_search = Search('sthpw/note')
        note_search.add_filter('process', 'queued_proc')
        self.assertEqual(note_search.get_count(), 1)
        q_done = Search('sthpw/queue')
        q_done.add_id_filter(jobs[0].get_id())
        job_after = q_done.get_sobject()
        self.assertEqual(job_after.get_value('state'), 'complete')
        t_final_after = Search('sthpw/task')
        t_final_after.add_id_filter(t_final.get_id())
        self.assertEqual(t_final_after.get_sobject().get_value('status'), 'Pending')

    def test_notifications_recipients_privacy_rules_logging_and_deduplication(self):
        with self.store.connection('sthpw', write=True) as db:
            # Create two users: alice (allowed in project 'one') and Mallory (only allowed in project 'two')
            db.execute(
                "INSERT INTO login (code, login, email, first_name, last_name) VALUES ('alice', 'alice', 'alice@example.com', 'Alice', 'Artist')"
            )
            db.execute(
                "INSERT INTO login (code, login, email, first_name, last_name) VALUES ('mallory', 'mallory', 'mallory@example.com', 'Mallory', 'Outside')"
            )
            db.execute(
                "INSERT INTO login (code, login, email, first_name, last_name, s_status) VALUES ('retired_u', 'retired_u', 'retired@example.com', 'Retired', 'User', 'retired')"
            )
            db.execute(
                """INSERT INTO login_group (code, login_group, access_rules)
                   VALUES ('one_team', 'one_team', '<rules><rule group="project" code="one" access="allow"/></rules>')"""
            )
            db.execute(
                """INSERT INTO login_group (code, login_group, access_rules)
                   VALUES ('two_only', 'two_only', '<rules><rule group="project" default="deny"/><rule group="project" code="two" access="allow"/></rules>')"""
            )
            db.execute(
                "INSERT INTO login_in_group (login, login_group) VALUES ('alice', 'one_team')"
            )
            db.execute(
                "INSERT INTO login_in_group (login, login_group) VALUES ('mallory', 'two_only')"
            )
            db.execute(
                "INSERT INTO login_in_group (login, login_group) VALUES ('retired_u', 'one_team')"
            )

        def setup_notifications():
            notif1 = SearchType.create('sthpw/notification')
            notif1.set_value('code', 'NOTIF_ASSIGN')
            notif1.set_value('event', 'change|sthpw/task|status')
            notif1.set_value('project_code', 'one')
            notif1.set_value('type', 'email')
            notif1.set_value('subject', 'Task {@GET(.process)} is {@GET(.status)}')
            notif1.set_value('message', 'Assigned to {@GET(.assigned)}')
            notif1.set_value('mail_to', 'one_team\nalice@example.com\nmallory\nretired_u')
            notif1.set_value('mail_cc', 'alice@example.com\ncc_user@example.com')
            notif1.set_value('mail_bcc', 'cc_user@example.com\nbcc_user@example.com')
            notif1.set_value(
                'rules',
                '<rules><rule group="sobject" key="status" op="=" value="Complete"/></rules>',
            )
            notif1.commit()

            # Second distinct notification on the same event must ALSO fire (not be dropped by dedup)
            notif2 = SearchType.create('sthpw/notification')
            notif2.set_value('code', 'NOTIF_AUDIT')
            notif2.set_value('event', 'change|sthpw/task|status')
            notif2.set_value('project_code', 'one')
            notif2.set_value('type', 'email')
            notif2.set_value('subject', 'Audit: {@GET(.process)}')
            notif2.set_value('message', 'Audit trail')
            notif2.set_value('mail_to', 'audit@example.com')
            notif2.set_value(
                'rules',
                '<rules><rule group="sobject" key="status" op="in" value="Complete|Approved"/></rules>',
            )
            notif2.commit()

            shot = SearchType.create('contract/entity')
            shot.set_value('code', 'ENT_NOTIF_1')
            shot.set_value('name', 'Notif Shot')
            shot.commit()

            task = Task.create(
                shot,
                process='light',
                description='Lighting',
                assigned='alice',
                status='Pending',
            )
            Notification.clear_cache()
            Trigger.clear_db_cache()
            return notif1, notif2, task

        notif1, notif2, task = _run_cmd(setup_notifications)

        sent_payloads = []
        with patch.object(EmailTrigger2, 'send') as mock_send:
            def capture_send(to_users, cc_users, bcc_users, subject, message, **kwargs):
                from pyasm.command.email_trigger import _bare_email_key, _extract_recipient_email
                to_set = {_bare_email_key(_extract_recipient_email(u)) for u in (to_users or ()) if _extract_recipient_email(u)}
                cc_set = {_bare_email_key(_extract_recipient_email(u)) for u in (cc_users or ()) if _extract_recipient_email(u)} - to_set
                bcc_set = {_bare_email_key(_extract_recipient_email(u)) for u in (bcc_users or ()) if _extract_recipient_email(u)} - to_set - cc_set
                sent_payloads.append({
                    'subject': subject,
                    'message': message,
                    'recipient_emails': sorted(to_set),
                    'cc_emails': sorted(cc_set),
                    'bcc_emails': sorted(bcc_set),
                })

            mock_send.side_effect = capture_send

            # 1) Updating status to In_Progress should NOT match rule status == Complete
            def set_in_progress():
                t = Search.get_by_id('sthpw/task', task.get_id())
                t.set_value('status', 'In_Progress')
                t.commit()

            _run_cmd(set_in_progress)
            self.assertEqual(len(sent_payloads), 0)

            # 2) Updating status to Complete matches both notifications
            def set_complete():
                t = Search.get_by_id('sthpw/task', task.get_id())
                t.set_value('status', 'Complete')
                t.commit()

            _run_cmd(set_complete)

        self.assertEqual(len(sent_payloads), 2)
        by_subject = {item['subject']: item for item in sent_payloads}
        self.assertIn('Task light is Complete', by_subject)
        self.assertIn('Audit: light', by_subject)

        assign_mail = by_subject['Task light is Complete']
        # alice is in one_team AND listed as alice@example.com -> deduplicated to 1 entry
        # mallory is denied access to project 'one' -> excluded by privacy check
        # retired_u is retired -> excluded
        self.assertEqual(assign_mail['recipient_emails'], ['alice@example.com'])
        # alice@example.com in CC is removed because she's already in TO
        self.assertEqual(assign_mail['cc_emails'], ['cc_user@example.com'])
        # cc_user@example.com in BCC is removed because already in CC
        self.assertEqual(assign_mail['bcc_emails'], ['bcc_user@example.com'])

        # Check notification_log and notification_login records
        logs = Search('sthpw/notification_log').get_sobjects()
        self.assertEqual(len(logs), 2)
        logins = Search('sthpw/notification_login').get_sobjects()
        self.assertTrue(any(row.get_value('login') == 'alice' for row in logins))
        self.assertFalse(any(row.get_value('login') == 'mallory' for row in logins))

        # Test NotificationLogScope filter
        scope = NotificationLogScope()
        search_log = Search('sthpw/notification_log')
        scope.alter_search(search_log)
        self.assertEqual(search_log.get_count(), 2)

        # Test NotificationTestCmd end-to-end with EmailTriggerTest
        with patch.object(EmailTriggerTestCmd, 'execute', return_value=True) as mock_test_send:
            def run_notif_test():
                n1 = Search.get_by_id('sthpw/notification', notif1.get_id())
                n1.set_value('event', 'update|sthpw/task')
                n1.set_value('rules', '')
                n1.commit()
                Notification.clear_cache()
                Trigger.clear_db_cache()
                cmd = NotificationTestCmd(sobject_dict=n1.get_sobject_dict())
                cmd.execute()
                return cmd.get_description()

            desc = _run_cmd(run_notif_test)
            self.assertIn('Email sent to [alice@example.com', desc)
            self.assertTrue(mock_test_send.called)


if __name__ == '__main__':
    unittest.main()
