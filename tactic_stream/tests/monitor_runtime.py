"""Faults exist only in this disposable integration-test worker."""
import os
from pathlib import Path
import sys
import time


def worker(settings, sockets, heartbeat, stop, slot):
    from tactic_stream.server import app as module
    from tactic_stream.server.startup import start_server
    original = module.create_app
    def create_app(data_dir, thread_count=None, **kwargs):
        app = original(data_dir, thread_count, **kwargs)
        @app.get('/_test/worker-pid')
        async def worker_pid():
            return os.getpid()
        @app.get('/_test/block-loop')
        async def block_loop():
            (Path(data_dir) / 'blocked.pid').write_text(str(os.getpid()))
            time.sleep(30)
            return 'completed'
        @app.get('/_test/block-pool')
        def block_pool():
            (Path(data_dir) / 'blocked.pid').write_text(str(os.getpid()))
            time.sleep(30)
            return 'completed'
        return app
    module.create_app = create_app
    start_server(settings, sockets, heartbeat, stop, slot)


def never_start(settings, sockets, heartbeat, stop, slot):
    time.sleep(30)


if __name__ == '__main__':
    from tactic_stream.server import monitor as module
    os.environ['TACTIC_DATA_DIR'] = str(Path(sys.argv[1]).resolve())
    module.start_server = never_start if sys.argv[2] == 'startup-hang' else worker
    module.TacticMonitor().execute()
