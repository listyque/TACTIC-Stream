// Use the same browser crypto primitive as Debug Log, including LAN HTTP.
export function randomId() {
  return [...crypto.getRandomValues(new Uint8Array(16))].map(value => value.toString(16).padStart(2, '0')).join('')
}

export function randomUuid() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const value = [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')
  return [value.slice(0, 8), value.slice(8, 12), value.slice(12, 16), value.slice(16, 20), value.slice(20)].join('-')
}
