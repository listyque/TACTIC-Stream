import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.ui.mjs'
import * as Document from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs'
import * as Preview from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs'
const element=(name,attrs=[],children=[])=>({type:1,name,attributes:attrs,children})
const tree={type:9,children:[element('config',[],[element('cards_example',[['layout','sobject-layout'],['columns','12']],[element('element',[['name','title'],['row','1'],['span','12']],[element('display',[['class','title']])])])])]}
const raw={project:'demo',searchType:'demo/asset',view:'cards_example',source:'',tree,xml:Document.serialize(tree),configuration:{revision:'R1',sources:[],views:['cards_example'],layout_templates:[],resolved:{configured:true}},templates:[{name:'blank',tree}],canWrite:true,canLoad:true,dirty:false,busy:false,uncertain:false,sampleItems:[{kind:'object',title:'Asset',record:{name:'Asset',count:0}}]}
let ui=State.initial(),data=raw;ui=State.synchronize(ui,UI.model(data,ui));assert.equal(ui.selected,'title');assert.equal(State.synchronize(ui,UI.model(data,ui)),ui,'stable synchronization cannot cause render loops')
const send=(event,override={})=>{const result=State.transition(ui,UI.model({...data,...override},ui),event);ui=result.ui;return result.commands}
assert.deepEqual(send({type:'save'}),[]);assert.equal(ui.confirmation,'')
send({type:'buffer',key:'title:row',value:'0'});assert.deepEqual(send({type:'number',key:'title:row',field:'row'}),[]);assert.equal(ui.error,'Enter a whole number within the allowed range');assert(State.pending(ui));assert.deepEqual(send({type:'check'}),[])
send({type:'buffer',key:'title:row',value:'2'});let commands=send({type:'number',key:'title:row',field:'row'});assert.equal(commands[0].type,'xml');assert.match(commands[0].value,/row="2"/);assert(!State.pending(ui))
commands=send({type:'change',field:'hidden',invert:true,value:true});assert(!commands[0].value.includes('hidden="true"'),'Visible=true clears the hidden flag')
send({type:'remove'});assert.equal(ui.confirmation,'remove');send({type:'keep'});assert.equal(ui.selected,'title');send({type:'remove'});assert.equal(send({type:'confirm'})[0].type,'xml')
ui={...State.initial(),selected:'title'};data={...raw,dirty:true,checked:raw.xml};send({type:'save'});assert.equal(ui.confirmation,'save');assert.deepEqual(send({type:'confirm'}),[{type:'save'}])
for(const event of [{type:'xml',value:'x'},{type:'change',field:'title',value:'x'},{type:'add',value:'button'},{type:'save'},{type:'check'}])assert.deepEqual(send(event,{uncertain:true}),[])
assert.deepEqual(send({type:'help'},{busy:true}),[{type:'help'}],'general Help remains available during requests')
ui={...State.initial(),newName:'duplicate'};data={...raw,configuration:{...raw.configuration,views:['duplicate']}};assert.deepEqual(send({type:'newView'}),[]);assert.equal(ui.error,'A view with this name already exists')
ui={...State.initial(),newName:'new_cards',template:'copy'};data=raw;commands=send({type:'newView'});assert.equal(commands[0].view,'new_cards');assert.match(commands[0].xml,/<new_cards /)
for(const width of [360,800,1100])for(const page of ['design','configuration','xml','changes','resolved'])for(const language of ['en','ru']){
 const state={...State.initial(),selected:'title',page,panel:'settings'},model=UI.model({...raw,preview:{item_layout:Document.describe(tree,raw.view)}},state),scene=UI.describe(model,state,width,740,language),ids=new Set()
 const walk=nodes=>nodes.forEach(node=>{assert(!ids.has(node.id),'duplicate '+node.id);ids.add(node.id);for(const key of ['x','y','width','height'])assert(Number.isFinite(node[key]),node.id+'.'+key);assert(node.width>=0&&node.height>=0,node.id);walk(node.children||[])})
 walk(scene.nodes)
}
for(const kind of Document.widgets){const layout=Document.describe(tree,raw.view);layout.elements[0]={...layout.elements[0],kind,options:{text:'<script>text</script>'}};const sample={...raw.sampleItems[0],snapshot_display:{size:1024,exists:false},knowledge:[{title:'Guide'}]},scene=Preview.describe(layout,sample,320,'title','en',1100);assert(scene.height>=0);assert(scene.nodes.length,kind)}
const unsafe=Document.describe(tree,raw.view);unsafe.elements[0]={...unsafe.elements[0],kind:'image',options:{text:'file:///private.png'}};const scene=Preview.describe(unsafe,raw.sampleItems[0],320,'title','en',1100);assert.equal(scene.nodes[0].children[0].source,'')
console.log('Layout Frame: shared pages, numeric validation, visibility, template copies, check-before-save, confirmations, unknown writes and bounded previews passed')
