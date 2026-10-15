import assert from 'node:assert/strict'
import {sections} from '../../src/tactic_stream/shared_ui/controls/forms/sections.ui.mjs'
import {metrics} from '../../src/tactic_stream/shared_ui/core/foundation.mjs'

const fields = [
  {kind:'Heading',id:'heading',title:'SERVER / Pipeline',dataLabel:true,description:'Description'},
  {id:'hidden',when:false,title:'Hidden'},
  {id:'name',title:'SERVER NAME',dataLabel:true,field:'name',description:'A long explanation '.repeat(18)},
  {kind:'ChoiceGrid',id:'type',field:'kind',options:[{value:'action',label:'Action'},{value:'condition',label:'Condition'},{value:'progress',label:'Progress'}],props:{value:'condition'}},
  {kind:'Button',id:'rules',title:'Process rules',props:{action:{type:'rules'}}},
  {kind:'Heading',id:'emptyHeading',title:'Empty'},
  {kind:'ChoiceGrid',id:'emptyChoices',options:[]}
]
for (const width of [240,360,720]) for (const style of ['md3','material5','fluent']) {
  const screen = sections(fields,width,'ru',false,style)
  assert.equal(screen.nodes[0].text,'SERVER / Pipeline','Server labels stay verbatim')
  const first = screen.nodes.find(node=>node.id==='section_heading')
  assert.ok(!first.children.some(node=>node.id==='hidden'))
  const name = first.children.find(node=>node.id==='name')
  assert.equal(name.height,metrics(style).controlHeight)
  assert.equal(name.enabled,false)
  assert.deepEqual(name.action,{type:'field',field:'name'})
  assert.equal(first.children.find(node=>node.id==='nameLabel').text,'SERVER NAME')
  const grid = first.children.find(node=>node.id==='type')
  assert.equal(grid.children[1].selected,true)
  assert.deepEqual(grid.children[1].action,{type:'field',field:'kind',value:'condition'})
  assert.equal(grid.children[1].enabled,false)
  assert.equal(first.children.find(node=>node.id==='rules').action.type,'rules')
  const description = first.children.find(node=>node.id==='nameDescription')
  assert.ok(name.y>=description.y+description.height || name.x>=description.x+description.width,'Label and field cannot overlap')
  function inside(parent) {
    for(const child of parent.children||[]) {
      assert.ok(child.x>=0 && child.y>=0 && child.width>=0 && child.height>=0,child.id)
      assert.ok(child.x+child.width<=parent.width+.01 && child.y+child.height<=parent.height+.01,child.id+' inside '+parent.id)
      inside(child)
    }
  }
  for(const card of screen.nodes.filter(node=>node.kind==='Box')) inside(card)
  assert.equal(screen.nodes.find(node=>node.id==='section_emptyHeading').children[0].height,0)
  assert.ok(screen.height>=Math.max(...screen.nodes.map(node=>node.y+node.height)))
}
console.log('Frame form sections: responsive rows, all styles, long captions, raw labels, disabled events and empty choices passed')
