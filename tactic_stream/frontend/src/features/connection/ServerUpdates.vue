<script setup>
// Handler ServerUpdateService: one request and cursor stream, with browser suspension.
import { watch, onBeforeUnmount } from 'vue'
import { serverUpdates } from '../../api.js'
import { networkSettings } from './networkSettings.js'
import { setUpdatesAvailable, updateDelay } from './updateRequests.js'
import { serverEventStream } from './serverEventStream.js'

const props = defineProps({ ticket: String, project: String, subscription: Object })
const emit = defineEmits(['batch', 'reset', 'connection', 'error', 'session-expired'])
let timer, controller, nextPoll = 0, generation = 0, busy = false, stopped = false, failures = 0, initial = true, resync = false
let cursors = {}
function schedule(delay = updateDelay(networkSettings.pollInterval, failures)) {
  clearTimeout(timer)
  if (!stopped) { nextPoll = Date.now() + delay; timer = setTimeout(poll, delay) }
}
async function poll() {
  if (stopped || busy || !props.ticket) return
  if (document.hidden || navigator.onLine === false) { schedule(); return }
  const context = generation
  const requestController = new AbortController()
  controller = requestController
  busy = true
  let delay
  let changeTimer, updateFailure
  const pendingChannels = new Set(), pendingTypes = new Set()
  let fetching = false
  function changed(value) {
    value.channels.forEach(name => pendingChannels.add(name))
    value.search_types.forEach(name => pendingTypes.add(name))
    if (!fetching && !changeTimer) changeTimer = setTimeout(readChanges, networkSettings.batchDelay)
  }
  async function readChanges() {
    changeTimer = null
    if (stopped || context !== generation || requestController.signal.aborted || !pendingChannels.size) return
    fetching = true
    const channels = [...pendingChannels], invalidated_types = [...pendingTypes]
    pendingChannels.clear(); pendingTypes.clear()
    try {
      const result = await serverUpdates(props.ticket, props.project, { ...cursors, ...props.subscription, channels, invalidated_types, heartbeat:false }, requestController.signal)
      if (!stopped && context === generation && !requestController.signal.aborted) receive(result)
    } catch (failure) { updateFailure = failure; requestController.abort() }
    finally { fetching = false; if (pendingChannels.size && !requestController.signal.aborted) changed({channels:[],search_types:[]}) }
  }
  try {
    const values = { ...cursors, presence_ttl: Math.max(90, networkSettings.pollInterval * 3) }
    if (networkSettings.updateMode === 'sse') {
      await serverEventStream('/admin/server-events', { ticket:props.ticket, project:props.project, ...values, ...props.subscription },
        (result, event) => { if (!stopped && context === generation) { if (event === 'changes') changed(result); else receive(result) } }, requestController.signal)
    } else {
      const result = await serverUpdates(props.ticket, props.project, values, requestController.signal)
      if (!stopped && context === generation) receive(result)
    }
  } catch (failure) {
    failure = updateFailure || failure
    if (stopped || context !== generation) return
    if (failure.name === 'AbortError' || document.hidden || navigator.onLine === false) return
    if (failure.code === 'authentication_failed') {
      stopped = true; clearTimeout(timer); setUpdatesAvailable(false); emit('session-expired'); return
    }
    failures++
    const transient = failure instanceof TypeError || failure.name === 'TimeoutError' || [408, 429, 500, 502, 503, 504].includes(failure.status)
    delay = transient ? updateDelay(networkSettings.pollInterval, failures) : updateDelay(30)
    if (transient) { resync = true; setUpdatesAvailable(false); emit('connection', false) }
    else setUpdatesAvailable(true)
    if (!transient || failures >= 5) {
      emit('error', failure.message)
      // A permission refusal proves the server responded.
      emit('connection', !transient && !!failure.status && failure.status < 500)
    }
  } finally {
    requestController.abort(); clearTimeout(changeTimer); changeTimer = null
    busy = false
    if (!stopped) { if (context === generation) schedule(delay); else resume() }
  }
}
function receive(result) {
    for (const [name, records] of [['message_after', result.messages], ['activity_after', result.activity]]) {
      const timestamps = (records || []).map(row => row.__event_timestamp__ || row.timestamp || '').filter(Boolean)
      if (timestamps.length) cursors[name] = timestamps.sort().at(-1)
    }
    if (result.reactionCursor) cursors.reaction_after = result.reactionCursor
    if (result.cacheCursor) cursors.cache_after = result.cacheCursor
    const reconnected = failures > 0 || resync
    failures = 0; resync = false; setUpdatesAvailable(true)
    emit('connection', true); emit('error', '')
    emit('batch', { ...result, projectCode: props.project, initialActivity: initial, initialMessages: initial, reconnected })
    initial = false
}
watch(() => [props.ticket, props.project], (_, previous) => {
  generation++; clearTimeout(timer); cursors = {}; initial = true
  if (networkSettings.updateMode === 'sse') controller?.abort()
  if (!previous || previous[0] !== props.ticket) { failures = 0; nextPoll = 0; setUpdatesAvailable(true) }
  emit('reset'); emit('error', ''); resume()
}, { immediate: true })
watch(() => networkSettings.updateMode, () => {
  generation++; resync = true; clearTimeout(timer); controller?.abort(); resume()
})
watch(() => JSON.stringify(props.subscription), () => {
  if (networkSettings.updateMode === 'sse') { generation++; resync = true; clearTimeout(timer); controller?.abort(); resume() }
})
watch(() => networkSettings.pollInterval, () => { if (networkSettings.updateMode === 'poll' && !busy && !failures) schedule() })
function resume() {
  if (stopped || busy) return
  if (document.hidden || navigator.onLine === false) { controller?.abort(); return }
  // Focus, online and Retry must not bypass a reconnect delay.
  const delay = failures ? Math.max(0, nextPoll - Date.now()) : 0
  if (delay) schedule(delay)
  else { clearTimeout(timer); poll() }
}
function visibility() { if (document.hidden) { resync = true; setUpdatesAvailable(false); controller?.abort() } else resume() }
function offline() { resync = true; setUpdatesAvailable(false); controller?.abort(); failures = Math.max(1, failures); emit('connection', false) }
document.addEventListener('visibilitychange', visibility)
window.addEventListener('offline', offline)
window.addEventListener('online', resume)
onBeforeUnmount(() => { stopped = true; generation++; clearTimeout(timer); controller?.abort(); setUpdatesAvailable(false); document.removeEventListener('visibilitychange', visibility); window.removeEventListener('offline', offline); window.removeEventListener('online', resume) })
defineExpose({ refresh: resume })
</script>

<template></template>
