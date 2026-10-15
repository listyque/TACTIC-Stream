"""Inspect objects produced by actual CherryPyStartup, without starting a listener."""
from __future__ import annotations
import platform


def inspect_registered_services(server):
    import cherrypy
    from tactic.ui_api.version import BUILD_VERSION
    required = ('Api', 'XMLRPC', 'UploadServer')
    root = getattr(getattr(cherrypy.root, 'tactic', None), 'default', None)
    if root is None:
        raise RuntimeError('Default TACTIC project was not registered')
    app = cherrypy.tree.apps.get('')
    services = []
    for name in required:
        obj = getattr(root, name, None)
        if obj is None:
            raise RuntimeError('Missing original TACTIC service: ' + name)
        path = '/tactic/default/' + name
        configured = dict(getattr(app, 'config', {}).get(path, {}))
        if name in ('Api', 'XMLRPC') and configured.get('tools.xmlrpc.on') is not True:
            raise RuntimeError('XML-RPC tool is not enabled in mounted application: ' + path)
        services.append({'path': path, 'class': type(obj).__module__ + '.' + type(obj).__name__,
                         'xmlrpc_enabled': configured.get('tools.xmlrpc.on') is True})
    return {'python': platform.python_version(), 'ui_version': BUILD_VERSION,
            'registered': services, 'native_api_mounted': '/api/ui/v2' in cherrypy.tree.apps,
            'listener_started': False, 'database_login_tested': False,
            'notice': 'Original startup ran. No HTTP login or CRUD was performed.'}
