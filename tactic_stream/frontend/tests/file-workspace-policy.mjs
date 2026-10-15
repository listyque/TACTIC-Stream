import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { runInNewContext } from 'node:vm'
import { test } from 'node:test'

// Exercise both production policies with translation/clipboard isolated.
const desktop=await readFile('D:/code/th_codex/thlib/ui/qml/FileWorkspaceMenus.js','utf8')
const browser=await readFile(new URL('../src/features/fileWorkspace/interaction.js',import.meta.url),'utf8')
const presentation=await readFile('D:/code/th_codex/thlib/ui/qml/FileWorkspacePresentation.js','utf8')
const scripts=[desktop.replace('.pragma library','')+presentation.replace('.pragma library',''),browser.replace(/^import .*$/gm,'').replaceAll('export function ','function ').replace('export default','const interaction=').replace('export const columns','const columns')]
const policies=scripts.map(source=>runInNewContext(source+';({selectionReason,dropReason,badges})',{qsTr:value=>value,t:value=>value}))
function context(rows,extra={}){
  const state={selection_records:Object.fromEntries(rows.map((row,index)=>[index,row])),selection_scope:'changes',view:'change',stream:'main',workspace:'work',streams:[{code:'main',writable:true}],locks:{},change:{code:'ours',state:'pending',stream:'main'},...extra}
  return [{state,controller:{current_user:'admin',application_project:'files'},busy:false},
    {selectionRecords:state.selection_records,selectionScope:state.selection_scope,selectionQuery:state.selection_query,view:state.view,stream:state.stream,workspace:state.workspace,streams:state.streams,locks:state.locks,change:state.change,login:'admin',project:'files',busy:false}]
}
const file={kind:'file',path:'folder/a.txt',stream:'main',parent:'ours',owner:'admin',workspace:'work',change_state:'pending',local_status:'modified'}
function reason(command,rows,extra={}){
  const contexts=context(rows,extra),values=policies.map((policy,index)=>policy.selectionReason(contexts[index],command))
  assert.equal(values[0],values[1],'Handler and Stream use equivalent selection semantics')
  return values[0]
}
test('mixed selections never silently operate on a subset or another changelist',()=>{
  assert.match(reason('checkout_ordinary',[file,{kind:'directory',path:'folder/'}]),/without folders/)
  assert.match(reason('move_files',[file,{...file,path:'b.txt',parent:'other'}]),/current owned pending/)
  assert.match(reason('remove_files',[file,{...file,change_state:'submitted'}]),/pending/)
  assert.match(reason('shelve_selected',[file,{...file,owner:'artist'}]),/owned/)
  assert.match(reason('rename_file',[file,{...file,path:'b.txt'}]),/one file/)
  assert.match(reason('submit',[{kind:'change',code:'ours'},{kind:'change',code:'other'}]),/one changelist/)
  assert.equal(reason('move_files',[file]),'')
})

test('desktop deletion accepts whole empty lists and rejects mixed or unsafe selections',()=>{
  const change={kind:'change',code:'ours',stream:'main',owner:'admin',state:'pending',opened_files:0}
  const reason=rows=>policies[0].selectionReason(context(rows)[0],'delete_change')
  assert.equal(reason([change]),'')
  assert.equal(reason([change,{...change,code:'second'}]),'')
  assert.equal(reason([change,{...change,code:'shelf',state:'shelved',opened_files:12}]),'')
  assert.match(reason([change,file]),/headers/)
  assert.match(reason([change,{...change,code:'foreign',owner:'artist'}]),/your pending/)
  assert.match(reason([change,{...change,code:'other',opened_files:2}]),/Move or revert/)
  assert.match(reason([{...change,active_transfer:'upload'}]),/Finish/)
  assert.match(reason([{...change,state:'submitted'}]),/pending/)
  assert.match(reason([{...change,depot_writable:false}]),/write access/)
})
test('rights, mapping exclusions and ordinary/exclusive locks explain their restrictions',()=>{
  assert.match(reason('mark_delete',[file],{streams:[{code:'main',writable:false}]}),/write access/)
  assert.match(reason('mark_delete',[{...file,depot_writable:false}],{streams:[]}),/write access/)
  assert.match(reason('submit',[file],{streams:[],change:{code:'ours',depot_writable:false}}),/write access/)
  assert.match(reason('checkout_ordinary',[file,{...file,path:'b.txt',writable:false}]),/read-only/)
  assert.match(reason('mark_delete',[file,{...file,path:'b.txt',stream:'other'}]),/one stream/)
  const locks={'main\0folder/a.txt':[{owner:'artist',workspace:'artist-work',mode:'ordinary'}]}
  assert.equal(reason('checkout_ordinary',[file],{locks}),'')
  assert.match(reason('checkout_exclusive',[file],{locks}),/checkout/)
  locks['main\0folder/a.txt']=[{owner:'admin',workspace:'another-machine',mode:'exclusive'}]
  assert.match(reason('checkout_ordinary',[file],{locks}),/checkout/)
  assert.match(reason('revert',[file],{change:{code:'ours',active_bulk:'job'}}),/Finish/)
})
test('local actions distinguish missing files, additions and modifications',()=>{
  assert.match(reason('open_local',[file,{...file,path:'b.txt',local_status:'missing'}]),/missing/)
  assert.equal(reason('reveal_local',[{...file,local_status:'missing'}]),'')
  assert.match(reason('apply_reconcile',[{...file,local_status:'clean'}]),/local changes/)
  assert.match(reason('stage_deletions',[file]),/missing local/)
})
test('drop targets reject foreign roots, streams, active work, self moves and malformed data',()=>{
  const target={kind:'change',state:'pending',code:'target',stream:'main',owner:'admin',workspace:'work'}
  const payload={project:'files',workspace:'work',scope:'changes',rows:[file]}
  for(let index=0;index<2;index++){
    const policy=policies[index],ctx=context([])[index]
    const drop=(value=payload,row=target)=>policy.dropReason(ctx,row,JSON.stringify(value),[])
    assert.equal(drop(),'')
    assert.match(drop(payload,{...target,stream:'other'}),/one changelist stream/)
    assert.match(drop(payload,{...target,active_transfer:'task'}),/Finish/)
    assert.match(drop(payload,{...target,code:'ours'}),/already/)
    assert.match(drop({...payload,project:'private'}),/current project/)
    assert.match(drop({...payload,rows:[null]}),/Invalid/)
    assert.match(drop(null),/Invalid/)
    assert.match(drop({...payload,rows:[{kind:'file'}]}),/Invalid/)
    assert.match(drop({...payload,rows:[{kind:'depot'}]}),/files, folders/)
    assert.equal(drop({...payload,scope:'changes',rows:[{kind:'change',state:'shelved',code:'shelf',stream:'main'}]}),'')
  }
})
test('combined states distinguish current uploaded edits from subsequent local edits',()=>{
  for(const policy of policies){
    const labels=row=>Array.from(policy.badges(row),badge=>badge.label)
    const uploaded={action:'write',change_state:'pending',local_status:'modified',staged_current:true}
    assert.deepEqual(labels(uploaded),['Modified','Uploaded'])
    assert.deepEqual(labels({...uploaded,staged_current:false}),['Modified after upload'])
    const busy=labels({...uploaded,staged_current:false,transfer_state:'verifying',conflict:true})
    assert.ok(busy.includes('Verifying'));assert.ok(busy.includes('Conflict'));assert.ok(busy.includes('Modified after upload'));assert.ok(!busy.includes('Uploaded'))
    assert.ok(labels({action:'write',change_state:'shelved'}).includes('Shelved'))
    assert.ok(labels({action:'write',change_state:'submitted'}).includes('Submitted'))
  }
})
