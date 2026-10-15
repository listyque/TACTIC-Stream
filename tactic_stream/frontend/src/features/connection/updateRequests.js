// Background reads have no queue: pause them while the shared update poll reconnects.
let available = true
const pending = new Map()
const unavailable = () => Object.assign(new Error('Unable to reach the server.'), { code: 'updates_unavailable' })

export function setUpdatesAvailable(value) {
  available = value
  if (!value) for (const { controller } of pending.values()) controller.abort(unavailable())
}

export function updatesAvailable() { return available }

export function backgroundRequest(key, request) {
  if (!available) return Promise.reject(unavailable())
  if (pending.has(key)) return pending.get(key).promise
  const controller = new AbortController()
  const entry = { controller }
  pending.set(key, entry)
  entry.promise = Promise.resolve().then(() => request(AbortSignal.any([controller.signal, AbortSignal.timeout(30000)])))
    .finally(() => { if (pending.get(key) === entry) pending.delete(key) })
  return entry.promise
}

export function updateDelay(interval, failures = 0, random = Math.random) {
  if (!failures) return Math.round(interval * 1000 * (0.85 + random() * 0.3))
  const base = failures < 5 ? 2000 * 2 ** (failures - 1) : failures === 5 ? 30000 : 60000
  return Math.round(base * (1 + random() * 0.25))
}
