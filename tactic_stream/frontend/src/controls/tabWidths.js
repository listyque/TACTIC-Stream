// Handler SearchWorkspaceView.qml fittedTabWidth: preserve the active tab,
// distribute remaining space across inactive tabs down to their native minimum.
export function fitTabWidths(natural, current, available, minimum) {
  const total = natural.reduce((sum, width) => sum + width, 0)
  if (total <= available || total <= natural.length * minimum) return natural.slice()
  const active = natural[current] || 0
  const inactiveMinimum = (natural.length - (current >= 0 ? 1 : 0)) * minimum
  const inactiveNatural = Math.max(inactiveMinimum, total - active)
  const remaining = available - active
  const ratio = remaining <= inactiveMinimum ? 0 : (remaining - inactiveMinimum) / (inactiveNatural - inactiveMinimum)
  return natural.map((width, index) => index === current ? width : remaining <= inactiveMinimum
    ? minimum : minimum + (width - minimum) * ratio)
}

// SearchWorkspaceView.qml displacedX, based on the dragged tab's own width.
export function displacedTabOffset(index, source, target, width) {
  if (source < 0 || target < 0) return 0
  if (source < target && index > source && index <= target) return -width
  if (source > target && index >= target && index < source) return width
  return 0
}
