// The same module runs in Qt's QML engine and in Vue; no Qt/DOM imports.
export function initial(screen) {
  return {draft: Object.assign({},screen.defaults), saved: Object.assign({},screen.defaults), error: '', applied: false, saves: 0}
}

export function transition(screen, state, event) {
  if (event.type === 'change') {
    if (!Object.prototype.hasOwnProperty.call(screen.defaults, event.field) || typeof event.value !== typeof screen.defaults[event.field]) throw Error('Invalid demo field')
    const draft=Object.assign({},state.draft);draft[event.field]=event.value
    return Object.assign({},state,{draft,error:'',applied:false})
  }
  if (event.type === 'reset') return Object.assign({},state,{draft:Object.assign({},state.saved),error:'',applied:false})
  if (event.type === 'apply') {
    if (!state.draft.name.trim()) return Object.assign({},state,{error:'Name is required'})
    const saved = Object.assign({},state.draft,{name:state.draft.name.trim()})
    return Object.assign({},state,{draft:Object.assign({},saved),saved,error:'',applied:true,saves:state.saves+1})
  }
  throw Error('Unsupported demo action: ' + event.type)
}

export function leaves(node) {
  if (node.children) {
    if (node.kind !== 'Row' && node.kind !== 'Column') throw Error('Unsupported layout: '+node.kind)
    return node.children.reduce((result,child)=>result.concat(leaves(child)),[])
  }
  if (['Label','TextField','CheckBox','Button'].indexOf(node.kind)<0) throw Error('Unsupported brick: '+node.kind)
  return [node]
}

export function layout(screen, width) {
  const boxes = {}
  function place(node, x, y, w, h) {
    boxes[node.id] = {x, y, width: w, height: h}
    if (!node.children) return
    const padding = node.padding || 0, gap = node.gap || 0
    x += padding; y += padding; w -= padding * 2; h -= padding * 2
    if (node.kind === 'Column') {
      for (const child of node.children) {place(child, x, y, w, child.height); y += child.height + gap}
    } else if (node.kind === 'Row') {
      const fixed = node.children.reduce((sum, child) => sum + (child.width || 0), 0) + gap * (node.children.length - 1)
      const growing = node.children.reduce((sum, child) => sum + (child.grow || 0), 0)
      if (node.align === 'end' && !growing) x += w - fixed
      for (const child of node.children) {
        const size = child.grow ? (w - fixed) * child.grow / growing : child.width
        place(child, x, y, size, h); x += size + gap
      }
    } else throw Error('Unsupported layout: ' + node.kind)
  }
  place(screen.layout, 0, 0, width, screen.viewport.height)
  return boxes
}

export function present(screen, state, language) {
  const translate = text => language === 'ru' ? screen.strings[text] || text : text
  const dirty = JSON.stringify(state.draft) !== JSON.stringify(state.saved)
  const status = state.error || (state.applied ? 'Saved' : dirty ? 'Unsaved changes' : 'Ready')
  const model={}
  for (const node of leaves(screen.layout)) model[node.id]={
    text: translate(node.status ? status : node.text || node.label || ''),
    value: node.field ? state.draft[node.field] : undefined,
    enabled: node.kind !== 'Button' || dirty,
    error: node.status && !!state.error
  }
  return model
}
