// Handler ActivationHandler.DragThreshold keeps a small release drift from losing the click.
export function capturePress(event) {
  const control = event.currentTarget
  if (event.button !== 0 || event.pointerType === 'touch' || control.disabled || control.getAttribute('aria-disabled') === 'true') return
  control.setPointerCapture(event.pointerId)
  const listeners = new AbortController(), x = event.clientX, y = event.clientY
  control.addEventListener('pointermove', move => {
    if (move.pointerId === event.pointerId && Math.hypot(move.clientX - x, move.clientY - y) >= 10) {
      if (control.hasPointerCapture(event.pointerId)) control.releasePointerCapture(event.pointerId)
      listeners.abort()
    }
  }, { signal:listeners.signal })
  for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) control.addEventListener(name, end => {
    if (end.pointerId === event.pointerId) listeners.abort()
  }, { signal:listeners.signal })
}
