###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ["EmailTrigger", "EmailTrigger2", "EmailTriggerThread", "SendEmail", "EmailTriggerTest", "EmailTriggerTestCmd"]

import datetime
import os
import re
import smtplib
import threading
import types
import six
from dateutil.relativedelta import relativedelta, MO as monday, FR
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate

from pyasm.common import Common, Config, Container, Environment, TacticException, Xml
from pyasm.biz import ExpressionParser, GroupNotification, Notification, ProdSetting, Project
from pyasm.security import Batch, Login, Site
from pyasm.search import ExceptionLog, SObject, SObjectValueException, Search, SearchType
from pyasm.command.command import Command, CommandException
from pyasm.command.trigger import Trigger
from . import email_handler as _email_handler_mod


def _extract_recipient_email(item):
    if isinstance(item, Login):
        return item.get_full_email() or item.get_value("email", no_exception=True) or ""
    if isinstance(item, SObject):
        return item.get_value("email", no_exception=True) or ""
    if isinstance(item, six.string_types):
        return item
    return ""


def _bare_email_key(value):
    text = str(value or "").strip().lower()
    if "<" in text and ">" in text:
        text = text.split("<", 1)[1].split(">", 1)[0].strip()
    return text


def _recipient_dedupe_key(item):
    if isinstance(item, Login):
        login = item.get_login()
        email = (item.get_value("email", no_exception=True) or "").strip().lower()
        return email or f"login:{login}"
    if isinstance(item, SObject):
        email = (item.get_value("email", no_exception=True) or "").strip().lower()
        return email or f"sobject:{item.get_search_key()}"
    return str(item or "").strip().lower()


class EmailTrigger(Trigger):

    def __init__(self):
        super(EmailTrigger, self).__init__()
        self.cmd_attrs = {}

    def get_title(self):
        return "EmailTrigger"

    def check(self):
        return True

    @classmethod
    def is_undoable(cls):
        return False

    def execute(self):
        command = self.get_command()
        if not command:
            return
        sobjects = command.get_sobjects()
        if not sobjects:
            msg = "Command [%s] has no sobjects.  Triggers cannot be called" % command.__class__.__name__
            Environment.add_warning("Command has no sobjects", msg)
            return
        self.notification_code = getattr(self, "notification_code", None)
        input = self.get_input()
        for sobject in sobjects:
            self.handle_sobject(sobject, command, input)

    def handle_sobject(self, main_sobject, command, input):
        search_type = main_sobject.get_search_type_obj().get_base_key()
        parent = None
        if main_sobject.has_value('search_type') and main_sobject.has_value('search_id'):
            parent = main_sobject.get_parent()
            if not parent:
                Environment.add_warning('Parent not found', 'Parent not found for task [%s]' % main_sobject.get_search_key())
                return
            if command.get_info('parent_centric') == True:
                search_type = parent.get_search_type_obj().get_base_key()

        search = Search("sthpw/notification")
        search.add_filter("search_type", search_type)
        search.add_project_filter()
        if getattr(self, "notification_code", None):
            search.add_filter("code", self.notification_code)
        notifications = search.get_sobjects()

        for notification in notifications:
            EmailTrigger2().handle_sobject(main_sobject, command, notification, input)

    def _process_sobject(self, sobject, rule_key, compare, input=None):
        if not sobject.has_value(rule_key):
            return False
        value = sobject.get_value(rule_key)
        if compare not in ["False", "false"]:
            prev_value = None
            has_input_prev = False
            if isinstance(input, dict):
                prev_data = input.get("prev_data")
                if isinstance(prev_data, dict) and rule_key in prev_data:
                    prev_value = prev_data.get(rule_key)
                    has_input_prev = True
            if not has_input_prev:
                prev_value = sobject.get_prev_value(rule_key)
            if value == prev_value:
                return False
        return True

    def get_email_handler(self, notification, sobject, parent, command, input={}):
        email_handler_cls = (notification.get_value("email_handler_cls", no_exception=True) or "").strip()
        if not email_handler_cls:
            email_handler_cls = "pyasm.command.EmailHandler"
        elif "." not in email_handler_cls and email_handler_cls in _email_handler_mod.__all__:
            email_handler_cls = "pyasm.command." + email_handler_cls
        return Common.create_from_class_path(
            email_handler_cls, [notification, sobject, parent, command, input]
        )

    @classmethod
    def add_email(cls, email_set, email):
        if email and email.find('@') > 0:
            email_set.add(email)

    @classmethod
    def send(cls, to_users, cc_users, bcc_users, subject, message, cc_emails=[], bcc_emails=[], from_user=None, reply_to_user=None):
        sender = set()
        to_emails = set()
        total_cc_emails = set()
        total_bcc_emails = set()

        if cc_emails:
            total_cc_emails.update(cc_emails)
        if bcc_emails:
            total_bcc_emails.update(bcc_emails)

        if from_user:
            sender.add(from_user)
            user_email = from_user
        else:
            login_obj = Environment.get_login()
            user_email = login_obj.get_full_email() if login_obj else ""
            if user_email:
                sender.add(user_email)
                from_user = user_email

            default_admin_email = Config.get_value("services", "mail_default_admin_email")
            if default_admin_email:
                from_user = default_admin_email

            site_email_name = Config.get_value("services", "mail_name")
            if site_email_name:
                site_email = Config.get_value("services", "mail_user")
                from_user = "%s <%s>" % (site_email_name, site_email)
                sender.add(from_user)

        if not reply_to_user:
            reply_to_user = user_email or from_user or ""

        for group_users, target_set in (
            (to_users, to_emails),
            (cc_users, total_cc_emails),
            (bcc_users, total_bcc_emails),
        ):
            for x in group_users or ():
                email = _extract_recipient_email(x)
                if not email:
                    continue
                if email.find(',') != -1:
                    for part in (y.strip() for y in email.split(',') if y.strip()):
                        cls.add_email(target_set, part)
                else:
                    cls.add_email(target_set, email.strip())

        to_bare = {_bare_email_key(e) for e in to_emails}
        total_cc_emails = {e for e in total_cc_emails if _bare_email_key(e) not in to_bare}
        cc_bare = {_bare_email_key(e) for e in total_cc_emails}
        total_bcc_emails = {e for e in total_bcc_emails if _bare_email_key(e) not in (to_bare | cc_bare)}

        st = 'html' if "</html>" in message else 'plain'
        msg = MIMEText(message, _subtype=st, _charset='utf-8')
        msg.add_header('Subject', subject)
        if from_user:
            msg.add_header('From', from_user)
        if reply_to_user:
            msg.add_header('Reply-To', reply_to_user)
        msg.add_header('To', ", ".join(sorted(to_emails)))
        msg.add_header('Cc', ", ".join(sorted(total_cc_emails)))
        msg.add_header('Bcc', ", ".join(sorted(total_bcc_emails)))
        msg.add_header('Date', formatdate(localtime=True))
        msg.add_header('html_encoding', 'base64')

        email_to_sender = ProdSetting.get_value_by_key('email_to_sender') or 'false'
        if email_to_sender in ['False', 'false']:
            recipients = total_bcc_emails | total_cc_emails | to_emails
        else:
            recipients = total_bcc_emails | total_cc_emails | to_emails | sender

        mailserver = Config.get_value('services', 'mailserver')
        if not mailserver or not recipients:
            return

        site = Site.get_site()
        project_code = Project.get_project_code()
        email = EmailTriggerThread(user_email or from_user or "", recipients, "%s" % msg.as_string(), site=site, project_code=project_code)
        email.start()


class SendEmail(Command):
    '''Class to send an email in a separate thread.'''

    def execute(self):
        sender_email = self.kwargs.get('sender_email')
        sender_name = self.kwargs.get('sender_name')
        paths = self.kwargs.get("paths") or []
        log_exception = self.kwargs.get("log_exception")

        if not sender_email:
            login_obj = Environment.get_login()
            sender_email = login_obj.get_full_email() if login_obj else ""
            if not sender_email:
                return

        recipient_emails = self.kwargs.get('recipient_emails') or []
        message = self.kwargs.get('msg') or ""

        st = 'html' if ("</html>" in message or paths) else 'plain'
        subject = self.kwargs.get('subject') or "Email Test"
        cc = self.kwargs.get('cc') or []
        bcc = self.kwargs.get('bcc') or []

        msg = MIMEMultipart()
        msg.add_header('Reply-To', sender_email)
        msg.add_header('To', ','.join(recipient_emails))
        msg.add_header('Date', formatdate(localtime=True))
        msg.add_header('Cc', ','.join(cc))
        msg.add_header('Bcc', ','.join(bcc))

        msg_text = MIMEText(message, _subtype=st, _charset='utf-8')
        msg.attach(msg_text)

        for path in paths:
            with open(path, "rb") as fil:
                part = MIMEApplication(fil.read(), Name=os.path.basename(path))
            part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(path)
            msg.attach(part)

        msg.add_header('Subject', subject)
        if sender_name:
            msg.add_header('From', "%s <%s>" % (sender_name, sender_email))
        else:
            msg.add_header('From', "%s" % sender_email)

        recipients = set(cc) | set(bcc) | set(recipient_emails)
        mailserver = Config.get_value('services', 'mailserver')
        if not mailserver or not recipients:
            return

        site = Site.get_site()
        project_code = Project.get_project_code()

        email = EmailTriggerThread(
            sender_email,
            recipients,
            "%s" % msg.as_string(),
            site=site,
            project_code=project_code,
            log_exception=log_exception,
        )
        email.start()

    @classmethod
    def is_undoable(cls):
        return False


class EmailTrigger2(EmailTrigger):

    def __init__(self):
        super(EmailTrigger, self).__init__()
        self.cmd_attrs = {}

    def get_title(self):
        return "EmailTrigger"

    def check(self):
        return True

    @classmethod
    def is_undoable(cls):
        return False

    def execute(self):
        caller = self.get_caller()
        if isinstance(caller, SObject):
            sobjects = [caller]
        elif caller is not None and hasattr(caller, "get_sobjects"):
            sobjects = caller.get_sobjects()
            if not sobjects:
                msg = "Caller has no sobjects.  Triggers cannot be called"
                Environment.add_warning("Caller has no sobjects", msg)
                return
        else:
            return

        notification = self.get_trigger_sobj()
        input = self.get_input()

        for sobject in sobjects:
            self.handle_sobject(sobject, caller, notification, input)

    def handle_sobject(self, main_sobject, caller, notification, input):
        parent = main_sobject.get_parent() if hasattr(main_sobject, "get_parent") else None
        input = input or {}

        snapshot = input.get('snapshot')
        env_sobjects = {}
        if snapshot:
            env_sobjects['snapshot'] = snapshot
        note = input.get('note')
        if note:
            env_sobjects['note'] = note

        rules_xml = notification.get_xml_value("rules")
        rule_nodes = rules_xml.get_nodes("rules/rule") if rules_xml else []
        is_skipped = True

        parser = ExpressionParser()

        for rule_node in rule_nodes:
            group_type = Xml.get_attribute(rule_node, "group")
            rule_key = Xml.get_attribute(rule_node, 'key')
            rule_value = Xml.get_attribute(rule_node, 'value')
            compare = Xml.get_attribute(rule_node, 'compare')
            op = Xml.get_attribute(rule_node, 'op')

            expression = Xml.get_node_value(rule_node)
            if expression:
                result = parser.eval(expression, main_sobject, env_sobjects=env_sobjects)
                if not result:
                    break
                else:
                    continue

            if group_type == "sobject":
                if not self._process_sobject(main_sobject, rule_key, compare, input=input):
                    break
                value = main_sobject.get_value(rule_key, no_exception=True)
            elif group_type == "parent":
                if not parent or not self._process_sobject(parent, rule_key, compare, input=input):
                    break
                value = parent.get_value(rule_key, no_exception=True)
            else:
                try:
                    value = caller.get_info(rule_key)
                except Exception:
                    value = ''

            if not value:
                break

            if op in ("=", "", None):
                if str(value) != str(rule_value):
                    break
            elif op == "!=":
                if str(value) == str(rule_value):
                    break
            elif op == "in":
                values = rule_value.split("|") if "|" in rule_value else [rule_value]
                if str(value) not in values and str(value) not in rule_value:
                    break
            elif op == "not in":
                values = rule_value.split("|") if "|" in rule_value else [rule_value]
                if str(value) in values or (len(values) == 1 and str(value) in rule_value):
                    break
            elif op == "?|":
                rule_values = rule_value.split("|")
                if isinstance(value, dict):
                    keys = list(value.keys())
                else:
                    keys = str(value).split("|")
                if not any(v in keys for v in rule_values):
                    break
            else:
                p = re.compile(rule_value)
                if not p.match(str(value)):
                    break
        else:
            is_skipped = False

        handler = self.get_email_handler(notification, main_sobject, parent, caller, input)
        if is_skipped or not handler.check_rule():
            self.add_description('Notification not sent due to failure to pass the set rules. Comment out the rules for now if you are just running email test.')
            return

        try:
            to_users = handler.get_to()
            if not to_users:
                return
            cc_users = handler.get_cc()
            bcc_users = handler.get_bcc()
        except SObjectValueException as e:
            raise Exception("Error in running Email handler [%s]. %s" % (handler.__class__.__name__, str(e)))

        def get_email():
            try:
                subject = handler.get_subject()
                subject = (subject or "").rstrip()
                if len(subject) > 60:
                    subject = subject[0:60] + " ..."
                message = handler.get_message() or ""
            except SObjectValueException as e:
                raise Exception("Error in running Email handler [%s]. %s" % (handler.__class__.__name__, str(e)))
            return (subject, message)

        send_email = handler.send_email()

        if handler.has_ticket():
            data = notification.get_json_value("data") or {}
            expiry = data.get("login_ticket_expiry") or 1
            unit = data.get("login_ticket_unit") or "day"

            today = datetime.datetime.today()
            if expiry == "next_monday":
                expiry_date = today + relativedelta(weekday=monday)
            elif expiry == "next_friday":
                expiry_date = today + relativedelta(weekday=FR)
            else:
                amount = int(expiry)
                if unit == "hour":
                    expiry_date = today + relativedelta(hours=amount)
                elif unit == "weeks":
                    expiry_date = today + relativedelta(weeks=amount)
                else:
                    expiry_date = today + relativedelta(days=amount)

            for to_user in to_users:
                handler.set_ticket(to_user, expiry_date)
                subject, message = get_email()
                self._send_to_users([to_user], cc_users, bcc_users, subject, message, send_email)
        else:
            subject, message = get_email()
            self._send_to_users(to_users, cc_users, bcc_users, subject, message, send_email)

    def _send_to_users(self, to_users, cc_users, bcc_users, subject, message, send_email):
        deduped_users = []
        seen_keys = set()
        email_list = []

        for items in (to_users, cc_users, bcc_users):
            for user in items or ():
                key = _recipient_dedupe_key(user)
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                deduped_users.append(user)
                if isinstance(user, six.string_types):
                    email = user
                else:
                    email = user.get_value('email', no_exception=True) or ""
                if email and email not in email_list:
                    email_list.append(email)

        project_code = Project.get_project_code()
        all_emails = ", ".join(email_list)

        self.add_notification(deduped_users, subject, message, project_code)

        if send_email:
            self.send(to_users, cc_users, bcc_users, subject, message)
            self.add_description('\nEmail sent to [%s]' % all_emails)

    @staticmethod
    def add_notification(all_users, subject, message, project_code, from_user=''):
        if not from_user:
            from_user = Environment.get_user_name()
        sobject = SearchType.create("sthpw/notification_log")
        sobject.set_user()
        sobject.set_value("subject", subject)
        sobject.set_value("message", message)
        sobject.set_value("project_code", project_code)
        Container.put("NotificationLog:writing", sobject)
        try:
            sobject.commit(triggers=False)
        finally:
            Container.remove("NotificationLog:writing")

        log_id = sobject.get_id()

        seen_logins = set()
        for to_user in all_users:
            if isinstance(to_user, Login):
                login = to_user.get_value("login")
            elif isinstance(to_user, SObject):
                login = to_user.get_value("login", no_exception=True) or to_user.get_value("email", no_exception=True)
            else:
                login = str(to_user or "")
            if not login or login in seen_logins:
                continue
            seen_logins.add(login)

            row = SearchType.create("sthpw/notification_login")
            row.set_value("notification_log_id", log_id)
            row.set_value("login", login)
            row.set_value("type", "to")
            row.set_value("project_code", project_code)
            Container.put("NotificationLog:writing", row)
            try:
                row.commit(triggers=False)
            finally:
                Container.remove("NotificationLog:writing")

        row = SearchType.create("sthpw/notification_login")
        row.set_value("notification_log_id", log_id)
        row.set_value("login", from_user)
        row.set_value("type", "from")
        row.set_value("project_code", project_code)
        Container.put("NotificationLog:writing", row)
        try:
            row.commit(triggers=False)
        finally:
            Container.remove("NotificationLog:writing")


class EmailTriggerThread(threading.Thread):
    '''Sending email as a separate thread'''
    def __init__(self, sender_email, recipient_emails, msg, site=None, project_code=None, log_exception=True):
        super(EmailTriggerThread, self).__init__()
        self.sender_email = sender_email
        self.recipient_emails = list(recipient_emails or ())
        self.msg = msg
        self.mailserver = Config.get_value('services', 'mailserver')
        self.user = Config.get_value('services', 'mail_user', True)
        self.password = Config.get_value('services', 'mail_password', True)
        if self.password and len(self.password) > 127 and hasattr(Common, 'unencrypt_password'):
            self.password = Common.unencrypt_password(self.password)

        self.port = Config.get_value('services', 'mail_port', True)
        self.mail_sender_disabled = Config.get_value('services', 'mail_sender_disabled', True) == 'true'
        self.mail_tls_enabled = Config.get_value('services', 'mail_tls_enabled', True) == 'true'
        self.port = int(self.port) if self.port else 25
        self.site = site
        self.project_code = project_code
        self.log_exception = log_exception

    def set_mailserver(self, mailserver):
        self.mailserver = mailserver

    def run(self):
        if not self.mailserver or not self.recipient_emails:
            return
        try:
            s = smtplib.SMTP(self.mailserver, self.port)
            if self.mail_tls_enabled:
                s.ehlo()
                s.starttls()
                s.ehlo()
            if self.user:
                s.login(self.user, self.password)
            if self.mail_sender_disabled:
                self.sender_email = ''
            s.sendmail(self.sender_email, self.recipient_emails, self.msg)
            s.quit()
        except Exception as e:
            message = "-" * 20 + "\n"
            message += "WARNING: Error sending email:" + str(e) + "\n"
            message += "mailserver: %s" % self.mailserver
            message += "port: %s" % self.port
            message += "sender: %s" % self.sender_email
            message += "recipients: %s" % self.recipient_emails

            if self.project_code and self.log_exception:
                try:
                    Batch(site=self.site, project_code=self.project_code)
                    ExceptionLog.log(e, message=message)
                except Exception:
                    print(message)
            else:
                print(message)


class EmailTriggerTestCmd(Command):
    '''This is run in the same thread for the email testing button'''
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.sender_email = self.kwargs.get('sender_email')

        if not self.sender_email:
            raise TacticException("Sender's email is empty.")
        self.recipient_emails = list(self.kwargs.get('recipient_emails') or ())
        message = self.kwargs.get('msg') or ""

        subject = self.kwargs.get('subject') or "Email Test"
        msg = MIMEText(message, _subtype='plain', _charset='utf-8')
        msg.add_header('Subject', subject)
        msg.add_header('From', self.sender_email)
        msg.add_header('Reply-To', self.sender_email)
        msg.add_header('To', ','.join(self.recipient_emails))
        msg.add_header('Date', formatdate(localtime=True))
        msg.add_header('html_encoding', 'base64')
        self.msg = msg

        self.mailserver = Config.get_value('services', 'mailserver')
        self.user = Config.get_value('services', 'mail_user', True)
        self.password = Config.get_value('services', 'mail_password', True)
        self.port = Config.get_value('services', 'mail_port', True)
        self.mail_sender_disabled = Config.get_value('services', 'mail_sender_disabled', True) == 'true'
        self.mail_tls_enabled = Config.get_value('services', 'mail_tls_enabled', True) == 'true'
        self.port = int(self.port) if self.port else 25

        super(EmailTriggerTestCmd, self).__init__(**kwargs)

    @classmethod
    def is_undoable(cls):
        return False

    def set_mailserver(self, mailserver):
        self.mailserver = mailserver

    def execute(self):
        if not self.mailserver:
            return
        try:
            s = smtplib.SMTP(self.mailserver, self.port)
            if self.mail_tls_enabled:
                s.ehlo()
                s.starttls()
                s.ehlo()
            if self.user:
                s.login(self.user, self.password)
            if self.mail_sender_disabled:
                self.sender_email = ''
            s.sendmail(self.sender_email, self.recipient_emails, self.msg.as_string())
            s.quit()
        except Exception as e:
            msg = [
                "-" * 60,
                "WARNING: Error sending email:",
                str(e),
                "mailserver: %s" % self.mailserver,
                "port: %s" % self.port,
                "sender: %s" % self.sender_email,
                "recipients: %s" % ','.join(self.recipient_emails),
            ]
            raise TacticException('\n'.join(msg))


class EmailTriggerTest(EmailTrigger2):
    '''Needed by Email Test button'''

    @classmethod
    def send(cls, to_users, cc_users, bcc_users, subject, message, cc_emails=[], bcc_emails=[]):
        sender = set()
        to_emails = set()
        total_cc_emails = set()
        total_bcc_emails = set()

        if cc_emails:
            total_cc_emails.update(cc_emails)
        if bcc_emails:
            total_bcc_emails.update(bcc_emails)

        login_obj = Environment.get_login()
        user_email = (login_obj.get_full_email() if login_obj else "") or Config.get_value("services", "mail_default_admin_email") or "admin@localhost"
        sender.add(user_email)

        for group_users, target_set in (
            (to_users, to_emails),
            (cc_users, total_cc_emails),
            (bcc_users, total_bcc_emails),
        ):
            for x in group_users or ():
                email = _extract_recipient_email(x)
                if not email:
                    continue
                if email.find(',') != -1:
                    for part in (y.strip() for y in email.split(',') if y.strip()):
                        cls.add_email(target_set, part)
                else:
                    cls.add_email(target_set, email.strip())

        to_bare = {_bare_email_key(e) for e in to_emails}
        total_cc_emails = {e for e in total_cc_emails if _bare_email_key(e) not in to_bare}
        cc_bare = {_bare_email_key(e) for e in total_cc_emails}
        total_bcc_emails = {e for e in total_bcc_emails if _bare_email_key(e) not in (to_bare | cc_bare)}

        recipient_emails = total_bcc_emails | total_cc_emails | to_emails | sender
        email = EmailTriggerTestCmd(
            sender_email=user_email,
            recipient_emails=recipient_emails,
            subject=subject,
            msg=message,
        )
        email.execute()
