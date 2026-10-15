// Use the same browser crypto primitive as Debug Log, including LAN HTTP.
export function randomId() {
  return [...crypto.getRandomValues(new Uint8Array(16))].map(value => value.toString(16).padStart(2, '0')).join('')
}
