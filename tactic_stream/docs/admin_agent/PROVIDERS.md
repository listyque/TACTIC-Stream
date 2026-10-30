# Provider connections

TS owns authenticated, per-login profile settings in `AgentProviderCmd`; TH is a
native settings/API client and does not store or execute API credentials. The
external `agent_host` owns Codex account execution, REST inference, model
discovery and MCP tool execution. No model code runs in the TS service process.
The chat and provider editor's **Connect agent / Disconnect agent** controls start
and stop a separate server-side host for the current account/project; see
[executor lifecycle](REQUESTS.md). They do not submit a model task or grant
additional TACTIC rights. Provider checks retrieve model catalogues without chat
data; sending project context still requires Send.

Open Configuration → AI providers, or the settings action in the normal chat.
Supported profiles: existing Codex account, OpenAI Responses, OpenAI-compatible
and local Chat Completions, Anthropic Messages, Gemini generateContent. Defaults
use official endpoints; compatible/local endpoints are operator configured.
HTTP is permitted only for the explicit local-server profile. Credentials never
follow redirects. Localhost refers to the external host machine.

Save uses an exact source revision and clears stale model discovery. Check asks
the owner's host to perform authenticated GET model discovery, without project
or chat data. Reports include a check nonce: stale results cannot overwrite a
changed profile. Failed checks do not invent model IDs. Choose a returned model
as default or choose one in the chat. Only actually advertised reasoning levels
are offered. An API listing a model does not establish tool/image compatibility.

## Credentials

`data/agent_providers/<sha256(login)>.json` contains encrypted credentials only.
Public state returns `has_secret`, never an API key. The write-only `secret`
argument uses existing RPC secret redaction. Alternatively `secret_env` names an
environment variable on the external host; TACTIC/Codex session variables cannot
be used as API keys. Model tools cannot manage or export provider credentials.

Windows uses DPAPI scoped to the server OS account; restoring to another account
or machine requires re-entering keys. Linux requires
`TACTIC_AGENT_VAULT_KEY_FILE`: an existing Fernet key file readable only by the
server account (0600). Create it once under that account, outside the source tree:

```python
from pathlib import Path
from cryptography.fernet import Fernet
with Path('/private/server-agent-vault.key').open('xb') as output:
    import os
    os.fchmod(output.fileno(), 0o600)
    output.write(Fernet.generate_key())
```

Set the environment variable for the server service/container and retain the
file across restarts. No key is generated implicitly during restore. Back up
encrypted profiles with local server settings and protect the vault separately;
database-only backups do not include these profile files. Losing either the
OS vault identity or Linux key requires re-entering credentials.

The host generates an ephemeral RSA key in memory and registers its public key
with its owner-scoped heartbeat. TS exports keys in RSA-OAEP/AES-GCM packages
bound to login, live host ID and profile ID. Another host/account cannot decrypt
that package. TS still requires HTTPS across untrusted networks for normal API
authentication. Host private keys are not persisted.

## Submitted data and execution

At Send, `AgentRequestCmd` captures provider ID, kind and base URL on that turn.
It is not taken from a later edited profile. API execution refuses a disabled,
deleted or changed destination. Changing connection/model is allowed between
turns and requires the next explicit Send. Old clients/chats retain Codex rather
than silently switching to an API default. Checks do not authorize inference.

Only the selected connection receives conversation text, captured project/page/
selection and the current submitted images or requested tool results. TACTIC
passwords/tickets, vault files and unrelated provider keys are excluded. Tool
results remain untrusted data. Binary attachments are metadata/tools, not a
universal document/audio/video decoder. The shared MCP operations preserve native
permissions, revisions, receipts, trial restrictions and inactive script drafts.
The loop supports cancellation and user corrections, bounded time/tool calls,
and explicit completed/needs_input/blocked outcomes. In-flight HTTP cancellation
waits for its bounded request to return; applied native operations remain.

Codex, OpenAI and Anthropic can use native web search when permitted. Compatible,
local and Gemini connections currently expose public direct-download tools but
no built-in search adapter. Do not claim that any model supports an unadvertised
feature. Protocol fixtures cover all vendors; paid/vendor inference needs actual
operator credentials and is a separate acceptance check.
