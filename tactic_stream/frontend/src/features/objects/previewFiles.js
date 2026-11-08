export async function fileBlob(file, { signal, preview = false } = {}) {
  if (!file?.href) throw new Error('No web path is configured for this file.');
  const response = await fetch(file.href, { signal });
  if (!response.ok) throw new Error('File Offline');
  return preview ? response : response.blob();
}

const textLimit = 100000;
const mediaTypes = {
  mp4: 'video/mp4',
  webm: 'video/webm',
  ogv: 'video/ogg',
  mp3: 'audio/mpeg',
  m4a: 'audio/mp4',
  wav: 'audio/wav',
  ogg: 'audio/ogg',
  flac: 'audio/flac'
};

export async function previewFile(file, loadFile, signal) {
  const suffix = file.filename?.split('.').at(-1)?.toLowerCase();
  const media = mediaTypes[suffix];
  if (file.href && media) {
    const url = new URL(file.href, location.href);
    if (
      ['http:', 'https:'].includes(url.protocol) &&
      document.createElement(media.split('/')[0]).canPlayType(media)
    )
      return { type: media, url: url.href };
  }
  const source = await loadFile(file, { signal, preview: true });
  const response = source instanceof Blob ? new Response(source) : source;
  const type = (response.headers.get('content-type') || '')
    .split(';')[0]
    .toLowerCase();
  if (
    type.startsWith('text/') ||
    ['application/json', 'application/xml'].includes(type)
  ) {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let remaining = textLimit,
      text = '';
    if (reader) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          text += decoder.decode(value.subarray(0, remaining), {
            stream: true
          });
          if (value.length > remaining) {
            await reader.cancel();
            return { type: 'text/plain', text, truncated: true };
          }
          remaining -= value.length;
        }
      } finally {
        reader.releaseLock();
      }
    }
    return { type: 'text/plain', text: text + decoder.decode() };
  }
  if (
    (type.startsWith('image/') && type !== 'image/svg+xml') ||
    type.startsWith('audio/') ||
    type.startsWith('video/') ||
    type === 'application/pdf'
  )
    return { type, blob: await response.blob() };
  await response.body?.cancel();
  return { type };
}
