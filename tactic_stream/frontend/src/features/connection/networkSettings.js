// Handler ServerUpdateService: network/serverUpdateInterval, seconds.
import { reactive, watch } from 'vue'
import { configurationPreview } from '../configuration/preferences.js'

export const updateIntervals = [5, 10, 30, 60].map(value => ({ value, label: `Every ${value} seconds` }))
export const updateModes = [{value:'poll', label:'Periodic checks'}, {value:'sse', label:'Server push (SSE)'}]
export const updateBatchDelays = [100, 200, 500, 1000].map(value => ({ value, label: `${value} ms` }))
let saved
try { saved = JSON.parse(localStorage.getItem('tactic_stream.network') || 'null') } catch { /* Native default. */ }
export const networkSettings = reactive({ pollInterval: updateIntervals.some(item => item.value === saved?.pollInterval) ? saved.pollInterval : 30,
  updateMode: saved?.updateMode === 'sse' ? 'sse' : 'poll',
  batchDelay: updateBatchDelays.some(item => item.value === saved?.batchDelay) ? saved.batchDelay : 200 })
watch(() => [networkSettings.pollInterval, networkSettings.updateMode, networkSettings.batchDelay], () => {
  if (configurationPreview.value) return
  try { localStorage.setItem('tactic_stream.network', JSON.stringify(networkSettings)) } catch { /* Current browser session still works. */ }
})
