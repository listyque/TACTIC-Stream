import { shallowReactive } from 'vue';

// Database timestamps are UTC; a missing offset is not the user's local time.
export function serverTimestamp(value) {
  const text = String(value || '')
    .trim()
    .replace(' ', 'T');
  return new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(text) ? text : text + 'Z');
}

export class ServerClock {
  constructor() {
    this.anchor = { utc: null, received: -Infinity, bestDelay: Infinity };
    this.revision = 0;
  }
  now() {
    this.revision;
    const { utc, received } = this.anchor;
    return utc === null ? Date.now() : utc + performance.now() - received;
  }
  observe(sample, started, received) {
    if (
      ![sample?.utcStarted, sample?.utcEnded].every(
        (value) =>
          typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
      )
    )
      return false;
    const anchor = this.anchor;
    const begin = Date.parse(sample.utcStarted),
      end = Date.parse(sample.utcEnded);
    const delay = received - started - (end - begin);
    if (
      ![begin, end, started, received].every(Number.isFinite) ||
      end < begin ||
      received < started ||
      delay < -2 ||
      received < anchor.received
    )
      return false;
    if (
      anchor.utc !== null &&
      delay > anchor.bestDelay * 1.5 + 20 &&
      received - anchor.received < 300000
    )
      return false;
    const utc = end + Math.max(0, delay) / 2;
    const changed =
      anchor.utc === null ||
      Math.abs(utc - anchor.utc - (received - anchor.received)) >= 500;
    anchor.utc = utc;
    anchor.received = received;
    anchor.bestDelay = Math.min(anchor.bestDelay, Math.max(0, delay));
    // Routine samples must not rerender every visible event and table timestamp.
    if (changed) this.revision++;
    return true;
  }
  observeResponse(response, started, received = performance.now()) {
    return this.observe(
      {
        utcStarted: response.headers.get('X-Tactic-UTC-Started'),
        utcEnded: response.headers.get('X-Tactic-UTC-Ended')
      },
      started,
      received
    );
  }
}
export const serverClock = shallowReactive(new ServerClock());
export const localTimeZone = () =>
  Intl.DateTimeFormat().resolvedOptions().timeZone;
