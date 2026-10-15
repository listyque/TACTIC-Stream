import assert from 'node:assert/strict'
import { bindingValue, layoutUrl, layoutElements, itemVariant } from '../src/features/interface/itemLayout.js'

const node={kind:'object',record:{name:'<script>alert(1)</script>',count:0},note_count:3}
assert.equal(bindingValue('record.name',node),'<script>alert(1)</script>')
assert.equal(bindingValue('record.count',node),0)
assert.equal(bindingValue('node.note_count',node),3)
assert.equal(bindingValue('node.constructor.prototype',node),'')
assert.equal(bindingValue('record.missing',node),'')
for(const url of ['javascript:alert(1)','JaVaScRiPt:alert(1)','data:text/html,test','//evil.example','/\\evil.example','https:\n//evil.example'])assert.equal(layoutUrl(url),'',url)
for(const url of ['/admin/preview?key=123','https://example.com/reference','mailto:user@example.com'])assert.equal(layoutUrl(url),url)
assert.equal(layoutUrl('mailto:user@example.com',true),'')
assert.equal(layoutUrl('blob:https://example.com/image',true),'blob:https://example.com/image')
assert.equal(itemVariant({...node,depth:1}),'children')
assert.equal(itemVariant({kind:'branch',branch:{kind:'process'}}),'process')
const layout={elements:[{name:'main',parent:'',variant:'main'},{name:'child',parent:'',variant:'children'},{name:'hidden',parent:'',variant:'all',hidden:true}]}
assert.deepEqual(layoutElements(layout,node).map(item=>item.name),['main'])
assert.deepEqual(layoutElements(layout,{...node,depth:2}).map(item=>item.name),['child'])
console.log('Item layout bindings, variants and URL safety PASS')
