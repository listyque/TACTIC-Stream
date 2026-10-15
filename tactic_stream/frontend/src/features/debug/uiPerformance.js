// UiPerformanceMonitor from Handler ui_performance.py, adapted to browser frames (EPL-1.0).
import { shallowReactive } from 'vue'

export class UiPerformanceMonitor {
  constructor() {
    this.state = shallowReactive({ recording: false, samples: [], summary: { count: 0, overBudget: 0, p95: 0, maximum: 0 } })
    this.samples = []; this.pending = new Map(); this.serial = 0
    this.visible = false; this.frame = null; this.expiry = null; this.publication = null
    this.observe = event => this.input(event)
    this.visibility = () => { if (document.hidden) for (const id of [...this.pending.keys()]) this.finish(id, 'No frame') }
  }
  setRecording(value) {
    if (this.state.recording === value) return
    this.state.recording = value
    for (const kind of ['pointerdown', 'pointerup', 'keydown', 'wheel']) {
      if (value) document.addEventListener(kind, this.observe, { capture: true, passive: true })
      else document.removeEventListener(kind, this.observe, true)
    }
    if (value) document.addEventListener('visibilitychange', this.visibility)
    else document.removeEventListener('visibilitychange', this.visibility)
  }
  begin(action, owner = document.activeElement, operation = true) {
    if (!this.state.recording || document.hidden) return 0
    const host = owner?.closest?.('dialog[open], [popover]:popover-open') || null
    const id = ++this.serial
    this.pending.set(id, { sampleId: id, action, window: host?.getAttribute('aria-label') || document.title,
      handlerMs: -1, frameMs: -1, readyMs: -1, details: '', slow: false, status: 'Waiting for frame',
      started: performance.now(), host, operation, committedAt: null })
    if (this.pending.size > 64) this.finish(this.pending.keys().next().value, 'Superseded')
    if (!this.expiry) this.expiry = setInterval(() => {
      for (const [key, sample] of this.pending) if (performance.now() - sample.started > 5000) this.finish(key, 'No frame')
    }, 1000)
    this.scheduleFrame()
    return id
  }
  input(event) {
    if (event.type === 'keydown' && event.repeat) return
    const action = event.type === 'keydown' ? 'Keyboard' : event.type === 'wheel' ? 'Scroll'
      : event.pointerType === 'touch' ? (event.type === 'pointerdown' ? 'Touch' : 'Touch release')
      : event.type === 'pointerdown' ? 'Pointer press' : 'Pointer release'
    const host = event.target?.closest?.('dialog[open], [popover]:popover-open') || null
    if (action === 'Scroll' && [...this.pending.values()].some(sample => sample.action === action && sample.host === host)) return
    const id = this.begin(action, event.target, false)
    if (id) setTimeout(() => this.end(id), 0)
  }
  scheduleFrame() {
    if (this.frame !== null || !this.pending.size) return
    // Two animation callbacks bound a paint opportunity, not a GPU presentation acknowledgement.
    this.frame = requestAnimationFrame(() => {
      const synchronizedAt = performance.now()
      this.frame = requestAnimationFrame(() => {
        this.frame = null
        const now = performance.now()
        for (const [id, sample] of this.pending) {
          if (sample.host && (!sample.host.isConnected || !sample.host.getClientRects().length)) { this.finish(id, 'Window closed'); continue }
          if (sample.started > synchronizedAt) continue
          if (sample.frameMs < 0) sample.frameMs = now - sample.started
          if (sample.committedAt !== null && sample.committedAt <= synchronizedAt) {
            if (sample.operation) sample.readyMs = now - sample.started
            this.finish(id, 'Browser frame')
          }
        }
        this.scheduleFrame()
      })
    })
  }
  details(id, values) {
    const sample = this.pending.get(id)
    if (sample) sample.details = JSON.stringify(values)
  }
  end(id, status) {
    const sample = this.pending.get(id)
    if (!sample) return
    sample.handlerMs = performance.now() - sample.started
    sample.committedAt = performance.now()
    if (status) this.finish(id, status)
    else if (!sample.operation && sample.frameMs >= 0) this.finish(id, 'Browser frame')
  }
  finish(id, status) {
    const sample = this.pending.get(id)
    if (!sample) return
    this.pending.delete(id)
    const { started, host, operation, committedAt, ...record } = sample
    record.status = status
    record.slow = Math.max(record.handlerMs, record.frameMs) > 50
    this.samples = [record, ...this.samples].slice(0, 250)
    if (this.visible && !this.publication) this.publication = setTimeout(() => { this.publication = null; this.publish() }, 100)
    if (!this.pending.size) {
      clearInterval(this.expiry); this.expiry = null
      if (this.frame !== null) cancelAnimationFrame(this.frame)
      this.frame = null
    }
  }
  publish() {
    if (!this.visible) return
    const frames = this.samples.filter(sample => sample.frameMs >= 0).map(sample => sample.frameMs).sort((a, b) => a - b)
    this.state.samples = this.samples
    this.state.summary = { count: this.samples.length, overBudget: frames.filter(value => value > 50).length,
      p95: frames.length ? frames[Math.min(frames.length - 1, Math.floor(frames.length * .95))] : 0, maximum: frames.at(-1) || 0 }
  }
  setVisible(value) {
    this.visible = value
    if (value) this.publish()
    else { clearTimeout(this.publication); this.publication = null }
  }
  clear() {
    this.pending.clear(); this.samples = []
    clearInterval(this.expiry); this.expiry = null
    clearTimeout(this.publication); this.publication = null
    if (this.frame !== null) cancelAnimationFrame(this.frame)
    this.frame = null
    this.state.samples = []; this.state.summary = { count: 0, overBudget: 0, p95: 0, maximum: 0 }
  }
  copyResults() { return JSON.stringify(this.samples, null, 2) }
  reset() { this.setRecording(false); this.clear() }
}

export const uiPerformance = new UiPerformanceMonitor()
