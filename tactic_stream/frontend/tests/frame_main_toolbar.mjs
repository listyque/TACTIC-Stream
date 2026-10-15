import assert from 'node:assert/strict'
import {describe,positions} from '../../src/tactic_stream/shared_ui/shell/main_toolbar.ui.mjs'

for (const width of [320,360,640,720,900,1280,1920]) {
  for (const compact of [false,true]) for (const dccClient of [false,true]) for (const progressReveal of [0,.5,1]) {
    const scene=describe({width,compact,dccClient,progressReveal})
    const visible=scene.nodes.filter(node=>node.visible!==false)
    assert.equal(new Set(scene.nodes.map(node=>node.id)).size,scene.nodes.length)
    for (let index=1;index<visible.length;index++) assert(visible[index].x>=visible[index-1].x+visible[index-1].width,'No overlapping controls')
    if (compact || width>=720) assert(visible.at(-1).x+visible.at(-1).width<=width,'Chrome remains in viewport')
    assert(visible.every(node=>node.width>=0 && node.height===36))
    const controls=positions(scene)
    assert.equal(controls.mainDcc.visible,dccClient&&!compact,'Native DCC is an explicit capability')
    assert.equal(controls.mainQueue.visible,!compact,'Phone commands remain available in the settings menu')
    assert.equal(scene.connectionExpanded,width>=900)
    assert.equal(scene.dccExpanded,width>=1280)
    assert.equal(controls.mainActivity.width,36+(width<760?0:184)*progressReveal)
  }
}
console.log('Main toolbar: named controls, shared order/geometry, progress, desktop DCC and phone layout passed')
