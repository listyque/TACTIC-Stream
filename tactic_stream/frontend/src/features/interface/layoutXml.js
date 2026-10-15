// Only parsing is engine-specific. Nodes, edits and serialization are portable.
export function layoutTree(source){
 if(!source.trim())throw Error('Select a SObject layout configuration')
 if(/<!DOCTYPE|<!ENTITY/i.test(source))throw Error('Document types and XML entities are not supported')
 const document=new DOMParser().parseFromString(source,'application/xml')
 if(document.querySelector('parsererror')||document.documentElement.tagName!=='config')throw Error('Invalid configuration XML')
 function convert(node){
  if(node.nodeType===1)return {type:1,name:node.tagName,attributes:[...node.attributes].map(attr=>[attr.name,attr.value]),children:[...node.childNodes].map(convert)}
  if(node.nodeType===9)return {type:9,children:[...node.childNodes].map(convert)}
  if([3,4,7,8].includes(node.nodeType))return {type:node.nodeType,...(node.nodeType===7?{name:node.target}:{}),text:node.data}
  throw Error('Unsupported XML node')
 }
 return convert(document)
}
