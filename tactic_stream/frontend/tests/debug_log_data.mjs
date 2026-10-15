import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { debugLog, debugSettings, exportSession, installDebugLogging, logEvent, logRequest, parseSession, redact, requestPayload, setServerDebugContext } from '../src/features/debug/debugLog.js'
import { rpc } from '../src/api.js'

globalThis.location = { origin: 'http://tactic-stream.test' }
const reports = []
globalThis.fetch = async (url,options) => { reports.push({url,...JSON.parse(options.body)}); return {ok:true} }
const credentials = { ticket: 'test-ticket-value', password: 'test-password-value', headers: { Authorization: 'test-authorization-value', Cookie: 'test-cookie-value' } }
const body = requestPayload({ echo: Object.values(credentials).slice(0, 2).join(' '), ...credentials })
assert.equal(JSON.stringify(body).includes(credentials.ticket), false)
assert.equal(JSON.stringify(body).includes(credentials.password), false)
assert.equal(body.headers.Cookie, '<REDACTED>')
assert.equal(requestPayload({ method: 'get_ticket', args: ['admin', 'positional-password-value'] }).args[1], '<REDACTED>')
assert.equal(redact('positional-password-value'), '<REDACTED>')
const cycle = { password: 'cyclic-password-value' }; cycle.self = cycle
assert.equal(requestPayload(cycle).self, '<recursive reference>')
assert.equal(redact('cyclic-password-value'), '<REDACTED>')

setServerDebugContext({ticket:credentials.ticket,project:'cg_test'})
debugSettings.recordingLevels = []
logEvent({level:'ERROR',message:'Upload failed: '+credentials.ticket,group:'browser/test'})
assert.equal(reports.length,1,'Server errors are recorded even with local recording disabled')
assert.equal(reports[0].method,'log')
assert.deepEqual(reports[0].args[0],{ticket:credentials.ticket,project:'cg_test'})
assert.ok(!reports[0].args[2].includes(credentials.ticket),'Persisted messages redact credentials')
logEvent({level:'INFO',message:'Success'})
logRequest('/admin/server-updates',{ticket:credentials.ticket},null,new Error('offline'),0)
logRequest('/admin/rpc',{method:'log',args:[{ticket:credentials.ticket}]},null,new Error('diagnostics offline'),0)
assert.equal(reports.length,1,'Success, polling errors and logger requests do not send diagnostics')
globalThis.window = {addEventListener() {}}
const consoleError = console.error
console.error = () => {}
installDebugLogging()
console.error(new Error('Runtime diagnostic with local recording disabled'))
console.error = consoleError
assert.equal(reports.length,2,'Console errors reach the database with local recording disabled')
setServerDebugContext(null)
logEvent({level:'ERROR',message:'After sign-out'})
assert.equal(reports.length,2,'Signing out clears the authenticated diagnostic context')
debugSettings.recordingLevels = ['API', 'ERROR']
const command = 'print("🌍")\n' + 'long\n'.repeat(3000)
const original = [{ eventId: 8, timestamp: '2026-10-08T12:00:00', level: 'API', message: '<img src=x onerror=bad()>', module: 'api.js', functionName: 'query', group: 'admin/rpc', source: 'TACTIC API', command, duration: .3, sizeKb: 123.5 }]
const loaded = parseSession(exportSession(original))
assert.equal(loaded[0].command, command)
assert.equal(loaded[0].message, original[0].message)
assert.equal(loaded[0].duration, .3)
assert.throws(() => parseSession('{"v":2}\n'), /Unsupported/)
assert.throws(() => parseSession('{"v":1}\n{"id":1}\n{"id":1}\n'), /Invalid Debug Log event/)
assert.throws(() => parseSession('{"v":1}\n{"id":"NaN"}\n'), /Invalid Debug Log event/)
assert.throws(() => parseSession('{"v":1}\n{"m":{}}\n'), /Invalid Debug Log event/)
assert.throws(() => parseSession('{"v":1}\nBROKEN\n'), error => error.line === 2)
logRequest('/admin/rpc', { method: 'get_ticket', args: ['admin', credentials.password] }, { result: 'returned-ticket-value' }, null, .125)
logRequest('/admin/rpc', { method: 'query', args: [{ ticket: 'returned-ticket-value' }] }, { error: 'returned-ticket-value' }, new Error('returned-ticket-value'), .25)
const stored = exportSession(debugLog.entries)
assert.equal(stored.includes(credentials.password), false)
assert.equal(stored.includes('returned-ticket-value'), false)
logRequest('/tactic/cg_test/UploadServer/', { ticket: 'returned-ticket-value', file: { name: 'sample.png', size: 3 } }, ['sample.png'], null, .1)
const replay = spawnSync(process.env.STREAM_CHECK_PYTHON || 'python', ['-c', `import sys
from email.parser import BytesParser
from types import SimpleNamespace
from unittest.mock import patch
def upload(request):
    assert request.full_url == 'http://tactic-stream.test/tactic/cg_test/UploadServer/'
    message = BytesParser().parsebytes(('Content-Type: ' + request.get_header('Content-type') + '\\r\\n\\r\\n').encode() + request.data)
    fields = list(message.walk())[1:]
    assert fields[0].get_param('name', header='Content-Disposition') == 'login_ticket'
    assert fields[0].get_payload(decode=True) == b'<REDACTED>'
    assert fields[1].get_filename() == 'sample.png'
    assert fields[1].get_payload(decode=True) == b'\\x00\\xff\\n'
    return SimpleNamespace(__enter__=None)
class Response:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return b'[]'
def send(request):
    upload(request)
    return Response()
with patch('pathlib.Path', return_value=SimpleNamespace(name='sample.png', read_bytes=lambda: b'\\x00\\xff\\n')), patch('urllib.request.urlopen', side_effect=send):
    exec(compile(sys.stdin.read(), '<upload replay>', 'exec'))
`], { input: debugLog.entries.at(-1).command, encoding: 'utf8' })
assert.equal(replay.status, 0, replay.stderr)
await assert.rejects(rpc('query', [cycle]), error => error instanceof TypeError && /circular/i.test(error.message), 'Logging must preserve the original request failure')
console.log('PASS: credential redaction, positional login, cyclic values, complete JSONL roundtrip, malformed-session validation and multipart upload replay')
