import assert from 'node:assert/strict'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/schema/schema_delete.ui.mjs'
const model={identity:'cg/assets',schemaRevision:'R1',metadata:{table:'assets',schemaRevision:'R1',title:'Assets',project:'cg',objects:0,pipelines:[],sharedRegistration:true},canWrite:true,busy:false,deleting:false,uncertain:false,error:'',confirmation:''}
assert.deepEqual(UI.transition(model,{type:'delete'}),[])
assert.deepEqual(UI.transition({...model,confirmation:'cg/assets '},{type:'delete'}),[])
assert.deepEqual(UI.transition({...model,confirmation:'cg/assets'},{type:'delete'}),[{type:'delete'}])
for(const change of [{busy:true},{uncertain:true},{canWrite:false},{metadata:{...model.metadata,schemaRevision:'R2'}}])assert.deepEqual(UI.transition({...model,confirmation:'cg/assets',...change},{type:'delete'}),[])
assert.deepEqual(UI.transition({...model,deleting:true},{type:'close'}),[])
assert.deepEqual(UI.transition({...model,uncertain:true},{type:'reload'}),[])
assert.deepEqual(UI.transition(model,{type:'reload'}),[{type:'reload'}])
for(const width of [256,360,500])for(const sample of [model,{...model,canWrite:false,metadata:{...model.metadata,objects:2,references:[{type:'sthpw/task',count:2}],aliases:['other/assets']}},{...model,uncertain:true}]){
 const scene=UI.describe(sample,width,500,'ru');assert(scene.nodes.every(node=>node.width>=0&&node.height>=0));const destructive=scene.nodes.find(node=>node.id==='adminDeleteSearchTypeApply');assert.equal(destructive.enabled,false)
}
console.log('Search Type deletion: exact confirmation, revisions, read-only, unknown write and modal close protection passed')
