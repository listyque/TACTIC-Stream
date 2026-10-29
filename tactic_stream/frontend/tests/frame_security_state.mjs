import assert from 'node:assert/strict'
import * as State from '../../src/tactic_stream/shared_ui/features/administration/security/security.state.mjs'
import * as UI from '../../src/tactic_stream/shared_ui/features/administration/security/security.ui.mjs'
import {policy} from '../../src/tactic_stream/shared_ui/features/administration/admin.document.mjs'

const model={ready:true,canWrite:true,canLoad:true,busy:false,uncertain:false,dirty:false,pendingText:false,
 group:'G0',groups:[{identity:'G0',label:'Artists'}],groupDocument:{xml:'<rules/>',accessLevel:'none',project:'',subGroups:''},
 attributes:{group:'project',code:'demo',access:'allow'},selected:0,records:[{group:'project',code:'demo',access:'allow',ruleIndex:0}],
 metadata:{accessLevels:['none','low'],targets:{project:[{label:'Demo',attributes:{code:'demo'}}]},globalDefaultRulesByLevel:{none:'<rules/>'}},
 matrixRows:[{label:'Demo',attributes:{code:'demo'}}],matrixGroups:[{label:'Artists',identity:'G0'}],xmlSource:'<rules/>',jsonSource:'{}',inheritedSource:'<rules/>'}
const initial=State.synchronize(State.initial(),model,true)
let result=State.transition(initial,{...model,dirty:true},{type:'save'})
assert.equal(result.ui.confirmation,'save');assert.deepEqual(result.commands,[])
result=State.transition(result.ui,{...model,dirty:true},{type:'confirm'})
assert.deepEqual(result.commands,[{type:'save'}])
assert.equal(policy({...model,uncertain:true,dirty:true}).save,false)
assert.deepEqual(State.transition(initial,{...model,uncertain:true,dirty:true},{type:'save'}).commands,[])
result=State.transition({...initial,page:'xml'},model,{type:'text',value:'<rules><!--draft--></rules>'})
const draft=result.ui,pendingModel={...model,dirty:true,pendingText:State.pending(draft)}
assert.equal(State.pending(draft),true)
assert.deepEqual(State.transition(draft,pendingModel,{type:'scope',value:'technical'}).ui,draft)
assert.deepEqual(State.transition(draft,pendingModel,{type:'save'}).commands,[])
assert.equal(State.transition(draft,pendingModel,{type:'save'}).ui.confirmation,'')
assert.equal(State.synchronize(draft,{...model,xmlSource:'other'},false).text,draft.text,'model notifications preserve unapplied text')
assert.equal(State.transition(draft,pendingModel,{type:'discardText'}).ui.text,model.xmlSource)
assert.equal(State.transition({...initial,page:'inherited'},model,{type:'text',value:'change'}).ui.text,initial.text)
assert.equal(State.transition(initial,{...model,busy:true},{type:'scope',value:'technical'}).ui.scope,'project')
assert.deepEqual(State.transition(initial,model,{type:'navigateCell',row:0,column:0,dx:1,dy:0}).commands,[])
assert.deepEqual(State.transition(initial,model,{type:'navigateCell',row:0,column:0,dx:0,dy:0}).commands,[{type:'focusGrid',grid:'adminSecurityMatrix',row:0,column:0,id:'adminSecurityCell_0_0'}])
function inspect(nodes,ids=new Set()){
 for(const n of nodes){assert(!ids.has(n.id),n.id+' unique');ids.add(n.id);assert(n.width>=0&&n.height>=0,n.id);assert(Number.isFinite(n.x+n.y+n.width+n.height),n.id);if(n.kind==='Button')assert(n.icon,n.id+' has an action icon');inspect(n.children||[],ids)}
 return ids
}
function find(nodes,id){for(const n of nodes){if(n.id===id)return n;const child=find(n.children||[],id);if(child)return child}}
for(const language of ['en','ru'])for(const width of [360,800,1100])for(const [scope] of UI.scopes)for(const page of ['group','xml','rule','inherited']){
 const ui=State.synchronize({...initial,scope,page,editing:true},model,true)
 inspect(UI.describe(model,ui,width,694,language).nodes)
 inspect(UI.toolbar(model,ui,width,language).nodes)
 const grid={cellWidth:136,rowHeight:46}
 assert.equal(UI.cell(grid,{checked:true,locked:true},0,0,model,ui,language).nodes[0].enabled,false)
 const scene=UI.describe(pendingModel,{...draft,scope:'technical'},width,694,language)
 assert.equal(find(scene.nodes,'adminSecuritySource').readOnly,false,'editing a text draft remains possible')
}
const wideScene=UI.describe(model,initial,1100,740,'en')
assert(find(wideScene.nodes,'adminSecurityNavigation'))
for(const [scope] of UI.scopes)assert(find(wideScene.nodes,'adminSecurityTabIcon_'+scope)?.icon)
assert(find(wideScene.nodes,'adminSecurityContextDescription').text)
assert(find(UI.describe(model,initial,800,740,'en').nodes,'adminSecurityScope'))
inspect(UI.describe({...model,dirty:true},{...initial,confirmation:'save'},360,740,'ru').nodes)
const squareCell=UI.cell({cellWidth:156,rowHeight:46},{checked:true},0,0,model,initial,'en').nodes[0]
assert.equal(squareCell.radius,0)
assert.equal(find(squareCell.children,'adminSecurityAccess_0_0').text,'Allowed')
console.log('Access rules shared state, guards and all scope/page layouts passed')

const hierarchy = {...model,
 groups: [{identity:'G0',label:'Artists'}, {identity:'G1',label:'Reviewers'}, {identity:'G2',label:'Leads'}],
 groupDocuments: {G0: {subGroups:''}, G1: {subGroups:'Leads'}, G2: {subGroups:'Artists'}}}
assert.equal(State.inheritanceChoices(hierarchy).find(g=>g.identity==='G1').cycle, true)
assert.deepEqual(State.transition(initial,hierarchy,{type:'inheritGroup',identity:'G1'}).commands,[])
const cleanHierarchy = {...hierarchy, groupDocuments:{G0:{subGroups:''},G1:{subGroups:''},G2:{subGroups:''}}}
assert.deepEqual(State.transition(initial,cleanHierarchy,{type:'inheritGroup',identity:'G1'}).commands,
 [{type:'groupField',field:'subGroups',value:'Reviewers'}])
const existing = {...hierarchy,groupDocument:{...model.groupDocument,subGroups:'Reviewers|admin'}}
assert.deepEqual(State.transition(initial,existing,{type:'inheritGroup',identity:'G1'}).commands,
 [{type:'groupField',field:'subGroups',value:'admin'}], 'removing a cyclic source preserves other entries')
assert.deepEqual(State.transition(initial,{...cleanHierarchy,canWrite:false},{type:'inheritGroup',identity:'G1'}).commands,[])
assert.deepEqual(State.transition(draft,{...cleanHierarchy,pendingText:true},{type:'inheritGroup',identity:'G1'}).commands,[])
console.log('Inheritance choices reject cycles, preserve unknown entries and obey draft/ACL guards')

const toolsModel={...model,metadata:{...model.metadata,
 users:[{value:'artist',label:'Artist'}],agentTools:[{name:'agent_context',readonly:true},{name:'ts_tasks_save',readonly:false}],mcpTools:[]}}
assert.deepEqual(State.transition({...initial,scope:'effective'},toolsModel,{type:'effectiveUser',value:'artist'}).commands,
 [{type:'effectiveUser',login:'artist'}])
assert.deepEqual(State.transition(initial,{...toolsModel,dirty:true},{type:'effectiveUser',value:'artist'}).commands,[])
assert.deepEqual(State.transition(initial,toolsModel,{type:'effectiveUser',value:'unknown'}).commands,[])
assert.deepEqual(State.transition({...initial,scope:'agent_tool'},toolsModel,{type:'toolRead'}).commands,
 [{type:'toolPolicy',scope:'agent_tool',mode:'selected',names:['agent_context']}])
assert.deepEqual(State.transition({...initial,scope:'agent_tool'},{...toolsModel,canWrite:false},{type:'toolRead'}).commands,[])
assert.deepEqual(State.transition({...draft,scope:'agent_tool'},toolsModel,{type:'toolRead'}).commands,[])
assert.deepEqual(State.transition({...initial,scope:'mcp_tool'},toolsModel,{type:'toolToggle',name:'ts_tasks_save'}).commands,[])
console.log('Effective-user requests and tool policies obey saved-state, catalogue and ACL guards')

const featuresModel={...model,attributes:{group:'builtin',key:'view_side_bar',access:'view'},
 metadata:{...model.metadata,builtinPermissions:[{key:'view_side_bar',title:'View Side Bar'}]}}
const featuresUi={...initial,scope:'builtin',editing:true}
assert.deepEqual(State.transition(featuresUi,featuresModel,{type:'builtinTarget',value:'view_side_bar'}).commands,
 [{type:'target',attributes:{key:'view_side_bar'}}])
for(const blocked of [{...featuresModel,canWrite:false},{...featuresModel,busy:true}])
 assert.deepEqual(State.transition(featuresUi,blocked,{type:'builtinTarget',value:'view_side_bar'}).commands,[])
assert.deepEqual(State.transition(featuresUi,featuresModel,{type:'builtinTarget',value:'unknown'}).commands,[])
assert.deepEqual(State.transition({...featuresUi,text:'pending'},featuresModel,{type:'builtinTarget',value:'view_side_bar'}).commands,[])
const featureScene=UI.describe(featuresModel,featuresUi,1100,694,'en').nodes
assert.equal(find(featureScene,'adminBuiltinFeature').value,'view_side_bar')
assert(!find(featureScene,'adminAccessLevel_delete'))
assert(!find(featureScene,'adminAccessField_key'))
assert.equal(featuresModel.attributes.access,'view','viewing legacy access does not convert it')
assert(!find(UI.describe(model,featuresUi,1100,694,'en').nodes,'adminAccessLevel_allow'),'a rule from another section cannot be edited as a feature')
console.log('Feature choices, explanations, native-level preservation and draft/ACL guards passed')
