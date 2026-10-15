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

from pyasm.common import Base
__all__ = ['SObjectAttr']

class SObjectAttr(Base):
    '''defines the base class for all attributes that sobjects contain'''

    def __init__(self, name, sobject):
        self.name = name
        self.sobject = sobject
        self.options = {}

    def init(self):
        '''initialization function called after all the options have been
        set.  Implementations should override this if needed'''
        pass

    def set_name(self, name):
        self.name = name

    def set_sobject(self, sobject):
        '''all attributes know about their parent sobject and make use of
        the data as needed'''
        self.sobject = sobject

    def set_value(self, value):
        self.sobject.set_value( self.name, value )

    def get_value(self):
        return self.sobject.get_value( self.name )

    def get_xml_value(self):
        if self.sobject.has_value(self.name):
            return self.sobject.get_xml_value( self.name )
        else:
            from pyasm.biz import Snapshot
            return Snapshot.get_latest_by_sobject(\
                    self.sobject).get_xml_value( self.name )

    def get_web_display(self):
        '''function that gets display for viewing on the web'''
        return self.get_value().capitalize()

    def set_option(self,name,value):
        self.options[name] = value

    def get_option(self,name):
        value = self.options.get(name)
        if not value:
            return ""
        else:
            return value

    def check_security(self):
        return True
