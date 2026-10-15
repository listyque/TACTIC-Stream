// One context gesture for mouse, touch hold and ordinary accessible menu buttons.
export const contextActions = {
  mounted(element, binding) {
    let timer, start, held = false
    const cancel = () => { clearTimeout(timer); start = null }
    const owns = event => event.composedPath().find(node => node.contextActionsCleanup) === element
    const handlers = {
      contextmenu(event) { if (!owns(event) || event.target.closest('.workspace-menu')) return; event.preventDefault(); binding.value(event) },
      keydown(event) {
        if (!owns(event) || event.target.closest('.workspace-menu') || !(event.key === 'ContextMenu' || event.key === 'F10' && event.shiftKey)) return
        event.preventDefault(); event.stopPropagation()
        const box = element.getBoundingClientRect()
        binding.value({ clientX: box.left + 9, clientY: box.bottom })
      },
      pointerdown(event) {
        cancel(); held = false
        if (!owns(event) || event.pointerType !== 'touch' || event.isPrimary === false || event.target.closest('.workspace-menu')) return
        start = { x: event.clientX, y: event.clientY }
        timer = setTimeout(() => { held = true; binding.value(event) }, 500)
      },
      pointermove(event) { if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 10) cancel() },
      pointerup: cancel, pointercancel: cancel,
      click(event) { if (held) { event.preventDefault(); event.stopImmediatePropagation(); held = false } },
    }
    for (const [name, handler] of Object.entries(handlers)) element.addEventListener(name, handler, name === 'click')
    element.contextActionsCleanup = () => { cancel(); for (const [name, handler] of Object.entries(handlers)) element.removeEventListener(name, handler, name === 'click') }
  },
  beforeUnmount(element) { element.contextActionsCleanup?.(); delete element.contextActionsCleanup },
}
