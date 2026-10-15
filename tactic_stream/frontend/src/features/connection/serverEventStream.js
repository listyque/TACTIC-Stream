// SSE over POST: tickets and resume cursors stay in the body, never in the URL.
export async function serverEventStream(url, payload, onUpdate, signal) {
  const controller = new AbortController()
  let timer, reader
  const arm = () => { clearTimeout(timer); timer = setTimeout(() => controller.abort(new DOMException('Server update stream timed out.', 'TimeoutError')), 45000) }
  timer = setTimeout(() => controller.abort(new DOMException('Server update connection timed out.', 'TimeoutError')), 30000)
  try {
    const response = await fetch(url, { method:'POST', body:JSON.stringify(payload),
      headers:{ 'Content-Type':'application/json', Accept:'text/event-stream', 'X-Tactic-Client':'TACTIC Stream' }, cache:'no-store',
      signal:AbortSignal.any([signal, controller.signal]) })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw Object.assign(new Error(data.error || 'Request failed.'), { code:data.error_code, status:response.status })
    }
    if (!response.headers.get('Content-Type')?.startsWith('text/event-stream')) throw new TypeError('Invalid server update stream.')
    reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = '', event = '', data = []
    while (true) {
      const chunk = await reader.read()
      if (chunk.done) throw new TypeError('Server update stream closed.')
      arm(); buffer += decoder.decode(chunk.value, { stream:true })
      let end
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0,end).replace(/\r$/, '')
        buffer = buffer.slice(end+1)
        if (!line) {
          if (data.length) {
            const value = JSON.parse(data.join('\n'))
            if (event === 'error') throw Object.assign(new Error(value.error || 'Request failed.'), { code:value.error_code, status:value.status })
            if (event === 'updates' || event === 'changes') onUpdate(value, event)
          }
          event = ''; data = []
        } else if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
      }
    }
  } finally {
    clearTimeout(timer)
    controller.abort()
    if (reader) { await reader.cancel().catch(() => {}); reader.releaseLock() }
  }
}
