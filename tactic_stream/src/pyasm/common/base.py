# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""TACTIC framework base with request-local timers."""
import sys
import time

from .container import Container


class Base:
    __timing = 0

    def start_timer(self, name="top"):
        if not Container.has("Base:total:%s" % name):
            Container.put("Base:total:%s" % name, 0)
        Container.put("Base:start:%s" % name, time.time())

    def end_timer(self, name="top"):
        diff = time.time() - Container.get("Base:start:%s" % name)
        total = Container.get("Base:total:%s" % name) + diff
        Container.put("Base:total:%s" % name, total)
        Base.__timing += diff
        return total

    def error(self, msg):
        self.serror(msg)

    @staticmethod
    def serror(msg):
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()

__all__ = ["Base"]
