import { watch, onBeforeUnmount } from 'vue'

// Handler ScrollBar.takePaginationPermit: fill short pages; otherwise require user navigation.
export function usePagination(viewport, content, enabled, requestMore) {
  let armed = false, blocked = false, pointer = null, frame = 0, releaseFrame = 0, cleanup
  function check() {
    const element = viewport.value
    if (!element?.checkVisibility() || !element.clientHeight || blocked || !enabled()) return
    const underfilled = element.scrollHeight <= element.clientHeight + 1
    const atEnd = element.scrollTop + element.clientHeight >= element.scrollHeight - 2
    if (!underfilled && (!atEnd || !armed)) return
    armed = false
    requestMore()
  }
  function schedule() { cancelAnimationFrame(frame); frame = requestAnimationFrame(check) }
  function arm() { if (!blocked) armed = true }
  function wheel(event) { if (event.deltaY > 0) { arm(); check(); schedule() } }
  function key(event) {
    if (event.target !== viewport.value || !['ArrowDown', 'PageDown', 'End', ' '].includes(event.key) || (event.key === ' ' && event.shiftKey)) return
    arm(); check(); schedule()
  }
  function press(event) {
    const element = viewport.value, box = element.getBoundingClientRect()
    const inside = event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom
    if (!inside) return
    const gutter = event.clientX >= box.left + element.clientLeft + element.clientWidth || event.clientX < box.left + element.clientLeft
    armed = false
    if (gutter) { blocked = true; pointer = event.pointerId; cancelAnimationFrame(releaseFrame) }
    else if (event.pointerType === 'touch') arm()
  }
  function release(event) {
    if (event.pointerId !== pointer) return
    pointer = null
    // Native thumb release can still deliver position notifications in the following frames.
    releaseFrame = requestAnimationFrame(() => {
      releaseFrame = requestAnimationFrame(() => { blocked = false; check() })
    })
  }
  watch([viewport, content], ([element, body]) => {
    cleanup?.(); armed = false; blocked = false; pointer = null
    if (!element || !body) return
    const observer = new ResizeObserver(check)
    observer.observe(element); observer.observe(body)
    element.addEventListener('scroll', check, { passive: true })
    element.addEventListener('wheel', wheel, { passive: true })
    element.addEventListener('keydown', key)
    document.addEventListener('pointerdown', press, true)
    document.addEventListener('pointerup', release, true)
    document.addEventListener('pointercancel', release, true)
    cleanup = () => {
      observer.disconnect(); cancelAnimationFrame(frame); cancelAnimationFrame(releaseFrame)
      element.removeEventListener('scroll', check); element.removeEventListener('wheel', wheel); element.removeEventListener('keydown', key)
      document.removeEventListener('pointerdown', press, true); document.removeEventListener('pointerup', release, true); document.removeEventListener('pointercancel', release, true)
    }
  }, { flush: 'post' })
  onBeforeUnmount(() => cleanup?.())
  return { check, reset: () => { armed = false } }
}
