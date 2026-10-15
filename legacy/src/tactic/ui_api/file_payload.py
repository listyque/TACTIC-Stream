"""Private server-side file delivery descriptor; never serialized to browser JSON."""
from dataclasses import dataclass

@dataclass(frozen=True)
class FilePayload:
    path: str
    filename: str
    content_type: str = 'application/octet-stream'
    inline: bool = False
