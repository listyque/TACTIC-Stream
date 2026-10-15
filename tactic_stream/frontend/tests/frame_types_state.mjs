import assert from 'node:assert/strict'
import * as Types from '../../src/tactic_stream/shared_ui/features/administration/search_types/search_types.state.mjs'
import * as TypesUI from '../../src/tactic_stream/shared_ui/features/administration/search_types/search_types.ui.mjs'
import * as Naming from '../../src/tactic_stream/shared_ui/features/administration/naming/naming.state.mjs'
const model={ready:true,canWrite:true,canLoad:true,dirty:true,identity:'',document:{title:'',color:'',hasPipeline:true,columns:[]},metadata:{columns:{code:{data_type:'varchar'}},columnRemovalBlocks:{code:'identity'}},catalog:[]}
let ui={...Types.initial(),page:'details'}
let result=Types.transition(ui,model,{type:'page',value:'fields'});assert.equal(result.commands.length,0);assert.ok(result.ui.error)
model.document.title='Episodes'
result=Types.transition(ui,model,{type:'page',value:'fields'});assert.deepEqual(result.commands,[{type:'page',value:'fields'}])
for(const name of ['code','pipeline_code','Wrong Name','1field']){result=Types.transition({...ui,fieldName:name},model,{type:'addField'});assert.ok(result.ui.error,name);assert.deepEqual(result.commands,[])}
result=Types.transition({...ui,fieldName:'duration_minutes',fieldType:'integer'},model,{type:'addField'});assert.deepEqual(result.commands,[{type:'addField',name:'duration_minutes',columnType:'integer'}])
assert.deepEqual(Types.transition(ui,model,{type:'removeField',name:'code'}).commands,[])
assert.deepEqual(Types.transition(ui,{...model,canWrite:false},{type:'field',field:'title',value:'No'}).commands,[])
assert.equal(Types.transition(ui,{...model,identity:'demo/asset'},{type:'workflow',identity:'demo/assets'}).commands.length,1,'opening a workflow preserves the type draft')
result=Types.transition({...ui,confirmation:'discard'},{...model,uncertain:true},{type:'confirm'});assert.deepEqual(result.commands,[{type:'reload',force:true}])
const scene=TypesUI.describe(model,{...ui,page:'fields',editing:true},600,740,'en')
function find(nodes,id){for(const node of nodes){if(node.id===id)return node;const child=find(node.children||[],id);if(child)return child}}
assert(find(scene.nodes,'typeAddFieldHeading').y>=find(scene.nodes,'adminAutomaticPipelineField').y+70,'field entry follows the automatic field explanation')
const naming={ready:true,canWrite:true,canLoad:true,dirty:false,document:{},sample:{key:'demo/asset?code=A1'}}
ui=Naming.initial();result=Naming.transition(ui,naming,{type:'evaluate',execute:true});assert.equal(result.ui.confirmation,'execute');assert.deepEqual(result.commands,[])
assert.deepEqual(Naming.transition(result.ui,naming,{type:'confirm'}).commands,[{type:'evaluate',execute:true}])
ui=Naming.transition(ui,naming,{type:'version',value:''}).ui;result=Naming.transition(ui,naming,{type:'commitVersion'});assert.ok(result.ui.error);assert.deepEqual(result.commands,[])
ui=Naming.transition(result.ui,naming,{type:'version',value:'12'}).ui;result=Naming.transition(ui,naming,{type:'commitVersion'});assert.equal(result.ui.sampleVersion,null);assert.deepEqual(result.commands,[{type:'sample',field:'version',value:12}])
ui=Naming.transition(Naming.initial(),{...naming,dirty:true},{type:'select',identity:'N2'}).ui;assert.equal(ui.confirmation,'navigate');assert.deepEqual(Naming.transition(ui,naming,{type:'confirm'}).commands,[{type:'discard'},{type:'select',identity:'N2'}])
assert.deepEqual(Naming.transition(Naming.initial(),{...naming,uncertain:true},{type:'field',field:'context',value:'retry'}).commands,[])
console.log('Search Types/Naming: creation validation, protected fields, draft-preserving workflow, unknown writes, execution consent and numeric input passed')
