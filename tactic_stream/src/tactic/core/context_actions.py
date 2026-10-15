"""Original SubContextAction, moved out of the presentation package.
Copyright (c) 2009 Southpaw Technology. Repository MIT license applies.
"""
from pyasm.command import DatabaseAction
from pyasm.common import UserException

class SubContextAction(DatabaseAction):

    def execute(self):
        # do nothing
        pass

    def postprocess(self):

        sobject = self.sobject


        subcontext = self.get_value()
        context = sobject.get_value("context")

        # if it is a simple context and no subcontext provided, return
        if not subcontext and (not context or context.find('/') == -1):
            return


        # replace the new subcontext

        # if existing context is empty, raise UserException
        # avoid value like '/subcontext'

        if not context:
            raise UserException('A context should be filled in first before entering a subcontext.')

        if context.find("/") != -1:
            context, old_subcontext = context.split("/", 1)

        if subcontext.strip():
            context = "%s/%s" % (context, subcontext)
        elif subcontext.strip() == '':
            # the case of removing the subcontext
            context = context

        self.sobject.set_value("context", context)
        self.sobject.commit()

