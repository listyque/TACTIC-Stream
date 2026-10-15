// Match the native editor's readable XML while keeping custom elements and text.
export function graphXmlText(xml){
  if(!xml?.documentElement)return ''
  const escape=(value,attribute=false)=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"',attribute?'&quot;':'"').replaceAll('\t',attribute?'&#09;':'\t').replaceAll('\n',attribute?'&#10;':'\n').replaceAll('\r',attribute?'&#13;':'\r')
  function render(node,depth){
    if(node.nodeType===8)return '<!--'+node.data+'-->'
    if(node.nodeType===7)return '<?'+node.target+(node.data?' '+node.data:'')+'?>'
    if(node.nodeType===3||node.nodeType===4)return escape(node.textContent)
    const attributes=[...node.attributes].map(attr=>' '+attr.name+'="'+escape(attr.value,true)+'"').join(''),children=[...node.childNodes]
    if(!children.length)return '<'+node.tagName+attributes+' />'
    const content=children.some(child=>child.nodeType===1||child.nodeType===7||child.nodeType===8),mixed=children.some(child=>[3,4].includes(child.nodeType)&&child.textContent.trim())
    const body=content&&!mixed?'\n'+'  '.repeat(depth+1)+children.filter(child=>![3,4].includes(child.nodeType)||child.textContent.trim()).map(child=>render(child,depth+1)).join('\n'+'  '.repeat(depth+1))+'\n'+'  '.repeat(depth):children.map(child=>render(child,depth+1)).join('')
    return '<'+node.tagName+attributes+'>'+body+'</'+node.tagName+'>'
  }
  return render(xml.documentElement,0)
}
