"""Private immutable agent inputs, uploaded in bounded retry-safe chunks."""
import base64
import hashlib
import json
from pathlib import Path

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.config import config_file_lock
from pyasm.security.security import _require_admin
from .agent_request_cmd import identity, text

CHUNK = 384 * 1024
MAX_FILE = 64 * 1024 * 1024


def directory():
    scope = hashlib.sha256(json.dumps([Environment.get_user_name(), Project.get_project_code()]).encode()).hexdigest()
    return Path(Environment.get_data_dir()) / 'agent_inputs' / scope


def attachment(code):
    code = identity(code)
    root = directory()
    path = root / (code + '.json')
    if not path.is_file():
        raise ValueError('Agent attachment is unavailable')
    metadata = json.loads(path.read_text(encoding='utf-8'))
    content = root / (code + '.data')
    if not metadata.get('ready') or not content.is_file() or content.stat().st_size != metadata['size']:
        raise ValueError('Wait for the attachment upload to finish')
    return metadata, content


class AgentAttachmentCmd(Command):
    def execute(self):
        _require_admin()
        if self.kwargs.get('project_code') != Project.get_project_code():
            raise ValueError('Attachment project mismatch')
        code = identity(self.kwargs.get('attachment_id'))
        root = directory()
        root.mkdir(parents=True, exist_ok=True)
        manifest, content = root / (code + '.json'), root / (code + '.data')
        action = self.kwargs.get('action')
        with config_file_lock(root / (code + '.lock')):
            if action == 'start':
                from tactic_stream.server.api import upload_file_name
                name = upload_file_name(text(self.kwargs.get('name'), 256))
                size = self.kwargs.get('size')
                if type(size) is not int or not 0 <= size <= MAX_FILE:
                    raise ValueError('Each attachment must be at most 64 MB')
                metadata = dict(attachment_id=code, name=name, size=size, ready=False,
                                media_type=text(self.kwargs.get('media_type', ''), 128, empty=True))
                if manifest.is_file():
                    old = json.loads(manifest.read_text(encoding='utf-8'))
                    if any(old[key] != metadata[key] for key in ('name', 'size', 'media_type')):
                        raise ValueError('Attachment ID already has different contents')
                    self.info = old
                    return
                content.touch(exist_ok=False)
            else:
                if not manifest.is_file():
                    raise ValueError('Agent attachment is unavailable')
                metadata = json.loads(manifest.read_text(encoding='utf-8'))
                if action == 'append':
                    raw = self.kwargs.get('data')
                    if not isinstance(raw, str) or len(raw) > CHUNK * 4 // 3 + 4:
                        raise ValueError('Attachment chunk exceeds the limit')
                    data = base64.b64decode(raw, validate=True)
                    offset = self.kwargs.get('offset')
                    if type(offset) is not int or offset < 0 or offset + len(data) > metadata['size']:
                        raise ValueError('Invalid attachment offset')
                    with content.open('r+b') as output:
                        output.seek(0, 2)
                        end = output.tell()
                        if offset < end:
                            output.seek(offset)
                            if output.read(len(data)) != data:
                                raise ValueError('Repeated upload chunk has different contents')
                        elif offset == end and not metadata['ready']:
                            output.write(data)
                        else:
                            raise ValueError('Upload chunks must be contiguous')
                    self.info = dict(offset=content.stat().st_size)
                    return
                elif action == 'finish':
                    if content.stat().st_size != metadata['size']:
                        raise ValueError('Attachment upload is incomplete')
                    with content.open('rb') as source:
                        metadata.update(ready=True, sha256=hashlib.file_digest(source, 'sha256').hexdigest())
                elif action == 'preview':
                    import io
                    from PIL import Image, ImageOps
                    attachment(code)
                    if metadata['media_type'] not in ('image/png', 'image/jpeg', 'image/webp', 'image/gif'):
                        raise ValueError('Choose an image attachment')
                    try:
                        with Image.open(content) as source:
                            if source.width * source.height > 32_000_000:
                                raise ValueError('Image exceeds the thumbnail pixel limit')
                            source.thumbnail((320, 180))
                            preview = ImageOps.exif_transpose(source).convert('RGB')
                            output = io.BytesIO()
                            preview.save(output, 'JPEG', quality=80)
                    except (OSError, ValueError, Image.DecompressionBombError):
                        raise ValueError('Image preview is unavailable') from None
                    self.info = dict(url='data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode())
                    return
                elif action == 'read':
                    attachment(code)
                    offset = self.kwargs.get('offset', 0)
                    if type(offset) is not int or not 0 <= offset <= metadata['size']:
                        raise ValueError('Invalid attachment offset')
                    with content.open('rb') as source:
                        source.seek(offset)
                        data = source.read(CHUNK)
                    self.info = dict(metadata, offset=offset, data=base64.b64encode(data).decode(),
                                     next_offset=offset + len(data) if offset + len(data) < metadata['size'] else None)
                    return
                else:
                    raise ValueError('Unknown attachment operation')
            temporary = manifest.with_suffix('.tmp')
            temporary.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
            temporary.replace(manifest)
            self.info = metadata
