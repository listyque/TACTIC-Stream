export function downloadBlob(blob, filename) {
  const href = URL.createObjectURL(blob), link = document.createElement('a')
  link.href = href; link.download = filename; link.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
