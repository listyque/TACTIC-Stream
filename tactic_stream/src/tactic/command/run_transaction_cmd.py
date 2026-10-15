############################################################
#
#    Copyright (c) 2011, Southpaw Technology
#                        All Rights Reserved
#
#    PROPRIETARY INFORMATION.  This software is proprietary to
#    Southpaw Technology, and is not to be reproduced, transmitted,
#    or disclosed in any way without written permission.
#
#


from pyasm.common import Environment
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import Search, SearchType, SObject


class RunTransactionCmd(Command):

    def is_undoable():
        return False
    is_undoable = staticmethod(is_undoable)

    def execute(self):

        transaction_xml = self.kwargs.get("transaction_xml")
        if not isinstance(transaction_xml, (str, dict, SObject)):
            raise ValueError('Expected transaction XML, a transaction record or SObject')
        file_mode = self.kwargs.get("file_mode")
        if not file_mode:
            file_mode = 'delayed'

        # if the first argument is a dictionary, then the whole
        # transaction sobject was passed through
        # NOTE: this is now the default
        if isinstance(transaction_xml, dict):
            transaction_dict = transaction_xml
            transaction_xml = transaction_dict.get("transaction")
            timestamp = transaction_dict.get("timestamp")
            login = transaction_dict.get("login")

            # recreate the transaction
            transaction = SearchType.create("sthpw/transaction_log")
            for name, value in transaction_dict.items():
                if name.startswith("__"):
                    continue
                if name == 'id':
                    continue
                if value == None:
                    continue
                transaction.set_value(name, value)

        elif isinstance(transaction_xml, SObject):
            transaction = transaction_xml

        else:
            # Create a fake transaction.
            # This is only used for test purposes
            transaction = SearchType.create("sthpw/transaction_log")
            if transaction_xml:
                transaction.set_value("transaction", transaction_xml)
            else:
                print("WARNING: transaction xml is empty")
            transaction.set_value("login", "admin")
            transaction.set_value('namespace', Project.get_project_code())

        transaction_code = transaction.get_value("code")
        if not transaction.get_value('transaction'):
            raise ValueError('Transaction instructions are required')

        # see if this transaction already exists
        if transaction_code:
            search = Search("sthpw/transaction_log")
            search.add_filter("code", transaction_code)
            if search.get_count():
                print("WARNING: transaction [%s] already exists" % transaction_code)
                return



        security = Environment.get_security()
        ticket = security.get_ticket_key()

        # run the transaction in the project of the transaction
        project_code = transaction.get_value("namespace")
        Project.set_project(project_code or Project.get_project_code())

        # NOTE: this is needed for operations, but does not
        # need to be committed
        transaction.set_value("ticket", ticket)

        # files mode is delayed then ignore file operations
        if file_mode == 'delayed':
            ignore = ['file']
        else:
            ignore = []
        #ignore = []


        # this will switch to use rel_path in transaction to get the files
        base_dir = self.kwargs.get("base_dir")

        transaction_log = transaction

        # Run the transaction
        from pyasm.command import RedoCmd
        cmd = RedoCmd(ignore=ignore, base_dir=base_dir, transaction_log=transaction)
        #Command.execute_cmd(cmd)
        cmd.execute()

        # Add remote sync registration
        transaction_log.trigger_remote_sync()
