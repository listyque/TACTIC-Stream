"""Local cluster hooks; never evaluate class paths or accept public proxy headers."""
import json
import os
from pathlib import Path
import secrets


def enabled():
    return os.environ.get('TACTIC_CLUSTER_ROLE') in ('writer', 'reader')


def install_guard():
    """Call before server.execute(), covering native AND original service mounts."""
    if not enabled():
        return
    import cherrypy
    secret = os.environ.get('TACTIC_CLUSTER_SECRET', '')
    if len(secret) < 40:
        raise RuntimeError('Missing private cluster credential')

    def verify_gateway():
        request = cherrypy.request
        supplied = request.headers.get('X-Tactic-Cluster', '')
        if request.remote.ip not in ('127.0.0.1', '::1') or not secrets.compare_digest(supplied, secret):
            raise cherrypy.HTTPError(403, 'This worker only accepts its local gateway')
        cherrypy.response.headers['X-Tactic-Worker'] = os.environ['TACTIC_CLUSTER_WORKER_ID']
        cherrypy.response.headers['X-Tactic-Worker-Pid'] = str(os.getpid())

    cherrypy.tools.tactic_cluster_guard = cherrypy.Tool('before_request_body', verify_gateway, priority=1)
    cherrypy.config.update({'tools.tactic_cluster_guard.on': True})
    # Existing applications may already have their own config dictionaries.
    for app in cherrypy.tree.apps.values():
        app.merge({'/': {'tools.tactic_cluster_guard.on': True}})


def public_status():
    """Admin System Info data, not paths, secrets, tickets or process arguments."""
    if not enabled():
        return {'enabled': False}
    name = os.environ.get('TACTIC_CLUSTER_STATUS')
    try:
        state = json.loads(Path(name).read_text(encoding='utf-8'))
        allowed = ('state', 'workers', 'port', 'read_policy', 'write_policy', 'updated_at')
        return {'enabled': True, 'current_worker': os.environ['TACTIC_CLUSTER_WORKER_ID'],
                **{k: state[k] for k in allowed if k in state}}
    except (OSError, ValueError, TypeError):
        return {'enabled': True, 'state': 'status_unavailable',
                'current_worker': os.environ.get('TACTIC_CLUSTER_WORKER_ID')}
