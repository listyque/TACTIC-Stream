// LAN HTTP has no Clipboard API; the user-activated copy command still works.
export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      /* Try the browser copy command. */
    }
  }
  const previous = document.activeElement,
    input = document.createElement('textarea');
  input.value = text;
  input.readOnly = true;
  input.style.cssText = 'position:fixed;inset:0;width:1px;height:1px;opacity:0';
  const host = document.querySelector('dialog:modal') || document.body;
  host.append(input);
  try {
    input.focus();
    input.select();
    if (!document.execCommand('copy'))
      throw new Error('Clipboard access failed');
  } finally {
    input.remove();
    previous?.focus();
  }
}

export async function readClipboard() {
  if (!navigator.clipboard?.readText)
    throw new Error('Paste with Ctrl+V or the browser menu on HTTP.');
  return navigator.clipboard.readText();
}

export async function readClipboardImages() {
  // Manual paste remains available when the browser forbids programmatic reads.
  if (!navigator.clipboard?.read) return null;
  let items;
  try {
    items = await navigator.clipboard.read();
  } catch (error) {
    if (['NotAllowedError', 'SecurityError'].includes(error.name)) return null;
    throw error;
  }
  const files = [];
  for (const item of items) {
    const type = item.types.includes('image/png')
      ? 'image/png'
      : item.types.find((type) => type.startsWith('image/'));
    if (!type) continue;
    const extension =
      type === 'image/jpeg' ? 'jpg' : type.split('/')[1].split('+')[0];
    files.push(
      new File(
        [await item.getType(type)],
        'clipboard' +
          (files.length ? '-' + (files.length + 1) : '') +
          '.' +
          extension,
        { type }
      )
    );
  }
  if (!files.length) throw new Error('The clipboard does not contain an image');
  return files;
}

export async function copyImage(blob) {
  if (!navigator.clipboard?.write || !globalThis.ClipboardItem)
    throw new Error(
      'Copying an image requires HTTPS or localhost and clipboard permission.'
    );
  let png = blob;
  if (blob.type !== 'image/png') {
    const image = await createImageBitmap(blob),
      canvas = document.createElement('canvas');
    try {
      canvas.width = image.width;
      canvas.height = image.height;
      canvas.getContext('2d').drawImage(image, 0, 0);
      png = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    } finally {
      image.close();
    }
    if (!png) throw new Error('Unable to copy image');
  }
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': png })]);
}
