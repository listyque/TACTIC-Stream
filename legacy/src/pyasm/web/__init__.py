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


try:
    import tacticenv
    import sys
    tactic_install_dir = tacticenv.get_install_dir()

    sys.path.insert(0, "%s/3rd_party/common/site-packages" % tactic_install_dir)
    if sys.version_info[0] < 3:
        sys.path.insert(0, "%s/3rd_party/python2/site-packages" % tactic_install_dir)
    else:
        if sys.version_info[1] <= 8:
            sys.path.insert(0, "%s/3rd_party/python3.6/site-packages" % tactic_install_dir)
        else:
            sys.path.insert(0, "%s/3rd_party/python3/site-packages" % tactic_install_dir)
except:
    pass

# web framework interface and implementations
from .web_environment import *
from .palette import *

from .callback import *

# security for redirects
from .url_security import *

# global web container
from .web_container import *
from .web_state import *

# basic widget classes
from .widget import *
from .html_wdg import *
from .web_tools import *

#from command_delegator import *
#from event_container import *

# the web application widget
from .web_app import *

from .web_login_cmd import *

from .app_server import *
from .simple_app_server import *
from .widget_app_server import *
from .web_init import *

from .monitor import *

from .cache_startup import *

