"""Classify native page requests without intercepting XML-RPC/REST/assets."""
from urllib.parse import unquote

RESERVED = {'Api','REST','GraphQL','UploadServer','ASSETS','GET','download','upload'}

def native_page(path, method='GET', accept='text/html', site=''):
    if method not in ('GET','HEAD') or 'text/html' not in accept:
        return False
    parts = [unquote(x) for x in path.strip('/').split('/') if x]
    if not parts: return True
    if parts[0] != 'tactic': return False
    if any(x in RESERVED for x in parts): return False
    if len(parts) == 1: return True
    if site and len(parts) > 1 and parts[1] == site: parts.pop(1)
    # /tactic/PROJECT, /index, /admin and links are native. Custom URL routes
    # remain untouched rather than being misinterpreted as admin screens.
    if len(parts) == 2: return True
    return parts[2] in ('index','admin','link')
