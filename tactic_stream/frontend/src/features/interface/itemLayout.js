import * as Layout from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs'
import {layoutTree} from './layoutXml.js'
export {widgets as layoutWidgets,roles as layoutRoles,actions as layoutActions,variants as layoutVariants,binding as bindingValue} from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs'

export function layoutUrl(value, image = false) {
  if (typeof value !== 'string' || !value.trim() || /[\u0000-\u0020\u007f\\]/.test(value)) return ''
  if (value.startsWith('/') && !value.startsWith('//')) return value
  try {
    const url = new URL(value)
    return (image ? ['https:', 'http:', 'blob:'] : ['https:', 'http:', 'mailto:', 'tel:']).includes(url.protocol) ? value : ''
  } catch { return '' }
}

export function itemVariant(node) {
  return node.kind === 'branch' ? node.branch?.kind || 'versions' : node.kind === 'object' ? (node.depth || node.ownerId ? 'children' : 'main') : node.kind
}

export function layoutElements(layout, node, parent = '') {
  const variant = itemVariant(node)
  return (layout?.elements || []).filter(item => !item.hidden && item.parent === parent && (item.variant === 'all' || item.variant === variant))
}

export function draftLayout(source,view){return Layout.describe(layoutTree(source),view)}
export function templateXml(source,view){return Layout.serialize(Layout.template(layoutTree(source),view))}
export function editLayout(source,view,name,field,value){return Layout.serialize(Layout.edit(layoutTree(source),view,name,field,value))}
