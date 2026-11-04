import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.ui.mjs'
import * as Process from '../../src/tactic_stream/shared_ui/features/administration/workflow/process.ui.mjs'
const model={mode:'workflow',ready:true,canWrite:true,canLoad:true,busy:false,dirty:true,uncertain:false,pendingText:false,identity:'P1',document:{name:'Assets',searchType:'cg/assets'},catalog:[],metadata:{nodeTypes:['manual','action','status'],pipelines:[],searchTypes:[]},nodes:[{identity:'model',label:'Model',nodeX:40,nodeY:40}],edges:[],selectedNode:'model',selectedNodes:['model'],selectedEdge:-1,processSettings:{},processKind:'manual',processProperties:{},processCatalog:{},xml:'<pipeline/>',attributes:'{}',settings:'{}'}
let ui=State.initial()
function send(event,context=model){const result=State.transition(ui,context,event);ui=result.ui;return result.commands}
send({type:'buffer',key:'attributes',value:'broken JSON'})
assert.deepEqual(send({type:'apply',key:'attributes'}),[]);assert.equal(ui.error,'Invalid JSON. Check quotes, commas and braces.')
assert.equal(send({type:'graph',value:{type:'selectNodes',identities:[],primary:''}}).length,0)
assert.equal(ui.confirmation,'selection')
send({type:'keep'});assert.equal(ui.text.attributes,'broken JSON')
assert.equal(send({type:'save'},{...model,pendingText:true}).length,0);assert.equal(ui.confirmation,'')
send({type:'graph',value:{type:'selectEdge',index:0}})
assert.deepEqual(send({type:'confirm'}),[{type:'selectEdge',index:0}]);assert.deepEqual(ui.text,{})
send({type:'remove'});assert.equal(ui.confirmation,'remove');assert.deepEqual(send({type:'confirm'}),[{type:'remove'}])
for(const type of ['save','addNode','moveNodes','setting','createWorkflow','createType','remove','layout'])assert.deepEqual(send({type,value:'x'},{...model,uncertain:true}),[],type)
send({type:'buffer',key:'integer_properties_duration',value:'2.5'})
assert.deepEqual(send({type:'integer',section:'properties',key:'duration',min:0,max:10}),[]);assert.equal(ui.error,'Enter a whole number within the allowed range')
send({type:'buffer',key:'integer_properties_duration',value:'12'})
assert.deepEqual(send({type:'integer',section:'properties',key:'duration',min:0,max:10}),[])
send({type:'buffer',key:'integer_properties_duration',value:'10'})
assert.deepEqual(send({type:'integer',section:'properties',key:'duration',min:0,max:10}),[{type:'setting',section:'properties',key:'duration',value:10}]);assert.equal(ui.error,'')
send({type:'selectPipeline',identity:'P2'});assert.equal(ui.confirmation,'navigate');assert.deepEqual(send({type:'confirm'}),[{type:'discard'},{type:'selectPipeline',identity:'P2'}])
assert.deepEqual(send({type:'dependencies'}),[]);assert.equal(ui.error,'Save the workflow before editing process dependencies')
assert.deepEqual(send({type:'dependencies'},{...model,dirty:false}),[{type:'dependencies'}])
assert.deepEqual(send({type:'description',value:'x'},{...model,busy:true}),[])
assert.deepEqual(send({type:'setting',key:'duration',section:'properties',value:20},{...model,canWrite:false}),[])
assert.equal(Process.value({...model,processProperties:{task_creation:false}},{section:'properties',key:'task_creation',initial:true}),false)
assert.deepEqual(Process.options({...model,processKind:'progress',processSettings:{progress:{related_pipeline_code:'P'}},processCatalog:{processes:[{identity:'PR1',label:'model',pipeline:'P'}]}},{options:'relatedProcesses'},'en'),[{value:'',label:'Not set'},{value:'PR1',label:'model'}])
for(const mode of ['schema','workflow'])for(const width of [360,800,1100])for(const language of ['en','ru']){
 const scene=UI.describe({...model,mode},State.initial(),width,740,language)
 const walk=nodes=>nodes.forEach(node=>{for(const key of ['x','y','width','height'])assert.ok(Number.isFinite(node[key]),node.id+'.'+key);assert.ok(node.width>=0&&node.height>=0,node.id);if(node.kind==='Graph')assert.equal(node.help,false);walk(node.children||[])})
 walk(scene.nodes)
}
console.log('Shared graph editor: drafts, selection, confirmation, ACL, unknown writes, integers and adaptive scenes passed')

const descendants = nodes => nodes.flatMap(node => [node, ...descendants(node.children || [])])
const parameterNodes = descendants(UI.inspector(model, State.initial(), 460, 'en').nodes)
assert.ok(parameterNodes.some(node => node.id === 'adminProcessDescription'))
assert.ok(!parameterNodes.some(node => node.id === 'adminGraphPositionX'), 'Coordinates must not precede process parameters')
assert.ok(!parameterNodes.some(node => node.id === 'adminGraphInspectorPages'), 'Workflow uses its process tabs, without duplicate Selection tabs')
const advancedNodes = descendants(UI.inspector(model, {...State.initial(), processPage:'native_json'}, 460, 'en').nodes)
assert.ok(advancedNodes.some(node => node.id === 'adminGraphPositionX'), 'Coordinate editing remains available')
assert.ok(parameterNodes.some(node => node.id === 'adminProcessKind'), 'Native type editing remains at the end of Parameters')
assert.ok(parameterNodes.findIndex(node => node.id === 'adminProcessField_task_pipeline') < parameterNodes.findIndex(node => node.id === 'processGroup_Appearance'), 'Task workflow precedes process fields as in Handler')
for (const width of [360, 1100]) {
 const nodes = descendants(UI.describe(model, State.initial(), width, 740, 'en').nodes)
 assert.ok(nodes.some(node => node.id === 'adminEditPipeline' && node.action.type === 'clear'), 'Dedicated Pipeline settings action')
 const ids = nodes.map(node => node.id)
 assert.equal(new Set(ids).size, ids.length, 'Controls have unique identities')
}

ui={...State.initial(), inspector:'add_node', propertiesVisible:false}
send({type:'buffer',key:'attributes',value:'{}'})
assert.deepEqual(send({type:'clear'}),[])
assert.equal(ui.confirmation,'selection')
assert.deepEqual(send({type:'confirm'}),[{type:'clear'}])
assert.equal(ui.inspector,'selection')
assert.equal(ui.propertiesVisible,true)

ui=State.initial()
send({type:'buffer',key:'instance',value:''})
assert.deepEqual(send({type:'commitInstance'}),[])
send({type:'buffer',key:'instance',value:'asset_links'})
assert.deepEqual(send({type:'commitInstance'}),[{type:'renameInstance',value:'asset_links'}])
assert.equal(State.completed(ui,{type:'renameInstance'}).text.instance,undefined)

const catalogModel={...model,dirty:false,catalog:[{identity:'P1',label:'Assets',searchType:'cg/assets',color:''}],metadata:{...model.metadata,searchTypes:[{identity:'cg/assets',label:'Assets',color:'#9bad77'}]}}
const catalogUi=State.initial(),flat=nodes=>nodes.flatMap(node=>[node,...flat(node.children||[])])
const rows=UI.models(catalogModel,catalogUi,'en').graphPipelines
const group=rows.find(row=>row.group&&row.searchType==='cg/assets'),pipeline=rows.find(row=>row.identity==='P1')
assert.equal(group.color,'#9bad77');assert.equal(pipeline.typeColor,'#9bad77')
assert(flat(UI.row({width:230,source:'graphPipelines'},group,catalogModel,catalogUi,'en').nodes).some(node=>node.background==='#9bad77'))
assert.equal(UI.row({width:230,source:'graphPipelines'},pipeline,catalogModel,catalogUi,'en').nodes[0].accent,'#9bad77')
assert.equal(UI.row({width:230,source:'graphPipelines'},{...pipeline,color:'#c08080'},catalogModel,catalogUi,'en').nodes[0].accent,'#c08080','Pipeline color remains independent')
const wideScene=UI.describe(catalogModel,catalogUi,1200,800,'en'),wideNodes=flat(wideScene.nodes)
assert.equal(wideNodes.find(node=>node.id==='adminWorkflowSearchTypeColor').background,'#9bad77')
for(const id of ['adminWorkflowCatalogPanel','adminGraphProperties']){
 const panel=wideNodes.find(node=>node.id===id)
 for(const button of panel.children.filter(node=>node.kind==='Button')){
  assert(button.x>=8&&button.y>=10,id+' header inset')
  assert(button.x+button.width<=panel.width-8,id+' right inset')
 }
}
assert(UI.describe(catalogModel,catalogUi,900,800,'en').nodes.some(node=>node.id==='adminGraphPanels'),'Narrow workflows use labelled panel tabs')
let schemaUi = State.initial();
for (const key of ['showColumns', 'showRoles', 'showCodes', 'showLegend']) {
  schemaUi = State.transition(schemaUi, { ...model, mode: 'schema' }, { type: 'toggleSchemaView', key }).ui;
  assert.equal(schemaUi[key], true);
}
const schemaScene = UI.describe(
  {
    ...model,
    mode: 'schema',
    metadata: { ...model.metadata, searchTypes: [{ identity: 'cg/shot', label: 'Shot', table: 'shot' }, { identity: 'cg/scenes', label: 'Episode', table: 'scenes' }] },
    nodes: [
      { identity: 'cg/shot', label: 'Shot', nodeX: 40, nodeY: 40, kind: 'search_type' },
      { identity: 'cg/scenes', label: 'Episode', nodeX: 320, nodeY: 40, kind: 'search_type' }
    ],
    edges: [{ from: 'cg/shot', to: 'cg/scenes', relationship: 'code', type: 'hierarchy' }]
  },
  schemaUi,
  1100,
  800,
  'ru'
);
const schemaFlat = flat(schemaScene.nodes);
assert.ok(schemaFlat.some((node) => node.id === 'adminSchemaLegendCard'), 'Schema legend card renders when toggled');
const schemaCanvas = schemaFlat.find((node) => node.id === 'adminGraphCanvas');
assert.deepEqual(schemaCanvas.edges[0].badgeLines, ['Child → Parent · иерархия', 'shot.scenes_code → scenes.code']);
let draftUi = State.initial();
let m2mRes = State.transition(
  draftUi,
  { ...model, mode: 'schema', nodes: [{ identity: 'cg/shot', label: 'Shot' }, { identity: 'cg/scenes', label: 'Episode' }] },
  { type: 'openConnectManyToMany', from: 'cg/shot' }
);
assert.equal(m2mRes.ui.inspector, 'add_node');
assert.equal(m2mRes.ui.connectMode, 'many_to_many');
assert.equal(m2mRes.ui.source, 'cg/shot');
let draftTableRes = State.transition(
  State.transition(draftUi, { ...model, mode: 'schema' }, { type: 'buffer', key: 'draftTable', value: 'props_asset' }).ui,
  { ...model, mode: 'schema' },
  { type: 'commitDraftTable' }
);
assert.deepEqual(draftTableRes.commands, [{ type: 'renameDraftTable', value: 'props_asset' }]);
const draftScene = UI.describe(
  {
    ...model,
    mode: 'schema',
    selectedNode: 'cg/draft_entity_1',
    selectedNodes: ['cg/draft_entity_1'],
    draftType: { table: 'draft_entity_1', title: 'Draft Entity 1', color: '#8899aa', hasPipeline: true },
    nodes: [{ identity: 'cg/draft_entity_1', label: 'Draft Entity 1', nodeX: 80, nodeY: 80, kind: 'search_type', draftType: true }],
    edges: []
  },
  draftUi,
  1100,
  800,
  'ru'
);
const draftFlat = flat(draftScene.nodes);
assert.ok(draftFlat.some((node) => node.id === 'adminRegisterDraftTypeNow'), 'Draft node inspector exposes 1-click DB registration');
assert.ok(parameterNodes.some((node) => node.id === 'processKindHeading'), 'Node type ChoiceGrid has its own dedicated section heading');
assert.ok(parameterNodes.some((node) => node.id === 'adminProcessKind_icon_action'), 'Node type ChoiceGrid options render icons');
const schemaNodesScene = UI.describe(
  {
    ...model,
    mode: 'schema',
    nodes: [
      { identity: 'cg/assets', label: 'Assets', nodeX: 40, nodeY: 40, kind: 'search_type' },
      { identity: 'cg/assets_in_assets', label: 'Assets in Assets', nodeX: 280, nodeY: 40, kind: 'search_type' },
      { identity: 'sthpw/task', label: 'Task', nodeX: 520, nodeY: 40, kind: 'search_type' }
    ],
    edges: [
      { from: 'cg/assets', to: 'cg/assets', instance_type: 'cg/assets_in_assets', relationship: 'instance' },
      { from: 'cg/assets_in_assets', to: 'cg/assets', relationship: 'code', from_col: 'parent_assets_code', to_col: 'code', path: 'child', type: 'many_to_many' },
      { from: 'cg/assets_in_assets', to: 'cg/assets', relationship: 'code', from_col: 'child_assets_code', to_col: 'code', path: 'parent', type: 'many_to_many' }
    ]
  },
  draftUi,
  1100,
  800,
  'en'
);
const graphCanvas = flat(schemaNodesScene.nodes).find((node) => node.id === 'adminGraphCanvas');
assert.equal(graphCanvas.nodes.find((n) => n.identity === 'cg/assets').visualKind, 'search_type');
const selfLinkNode = graphCanvas.nodes.find((n) => n.identity === 'cg/assets_in_assets');
assert.equal(selfLinkNode.visualKind, 'instance');
assert.equal(selfLinkNode.badgeText, 'SELF M:N');
assert.equal(selfLinkNode.subtitle, 'Assets ⇄ Assets · Self M:N');
assert.deepEqual(graphCanvas.edges[0].badgeLines, ['M:N · via assets_in_assets']);
assert.deepEqual(graphCanvas.edges[1].badgeLines, ['parent_assets_code → code (child)']);
assert.deepEqual(graphCanvas.edges[2].badgeLines, ['child_assets_code → code (parent)']);
assert.equal(graphCanvas.nodes.find((n) => n.identity === 'sthpw/task').visualKind, 'system');
