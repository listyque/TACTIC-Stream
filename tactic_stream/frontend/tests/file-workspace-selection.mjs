import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {runInNewContext} from 'node:vm'
const source=(await readFile(new URL('../src/features/fileWorkspace/interaction.js',import.meta.url),'utf8')).replace(/^import .*$/gm,'').replaceAll('export function ','function ').replace('export const columns','const columns').replace('export default','const interaction=')
const methods=runInNewContext(source+';interaction.methods',{t:value=>value})
const rows=Array.from({length:1000},(_,index)=>({id:String(index),row:{path:`local/${String(index).padStart(4,'0')}.txt`,kind:'file',local_status:index%2?'modified':'added'}}))
const context={selectionIds:[],selectionRecords:{},selected:[],scopeRows:()=>rows,selectedRows:methods.selectedRows}
let prevented=0
const event=key=>({key,ctrlKey:key==='a',preventDefault(){prevented++}})
methods.keySelection.call(context,event('a'),'files')
assert.equal(context.selectionIds.length,1000)
assert.equal(context.selected.length,1000)
assert.equal(context.selectionQuery,null)
methods.keySelection.call(context,event('Escape'),'files')
assert.equal(context.selectionIds.length,0)
context.scopeRows=()=>rows.filter(({row})=>row.path.startsWith('local/00')&&row.local_status==='modified')
methods.keySelection.call(context,event('a'),'files')
assert.equal(context.selected.length,50)
assert.equal(prevented,3)
console.log('Browser selection: 1000 loaded files, Escape and filtered selection passed')
