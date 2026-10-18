import assert from 'node:assert/strict'

export async function surface(page,selector,exclude){
 return page.locator(selector).evaluate((root,exclude)=>{
  const origin=root.getBoundingClientRect(),boxes={},styles={},fills={},canvas=document.createElement('canvas'),ctx=canvas.getContext('2d',{willReadFrequently:true})
  const color=value=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);return '#'+[...ctx.getImageData(0,0,1,1).data].slice(0,3).map(v=>v.toString(16).padStart(2,'0')).join('')}
  for(const el of root.querySelectorAll('[data-frame]')){
   if(exclude&&el.closest(exclude))continue
   if(!el.getClientRects().length||getComputedStyle(el).visibility==='hidden')continue
   if(el.tagName==='BUTTON'){const icon=el.__vueParentComponent?.props?.icon;if(icon&&!el.querySelector('.app-icon .icon-glyph')?.textContent)throw Error('Missing Frame button icon: '+el.dataset.frame+' / '+icon)}
   const r=el.getBoundingClientRect();if(r.width<=0||r.height<=0)continue;let visible=true
   for(let p=el.parentElement;p;p=p.parentElement){const css=getComputedStyle(p);if(/hidden|auto|scroll/.test(css.overflow+css.overflowX+css.overflowY)){const clip=p.getBoundingClientRect(),left=clip.left+p.clientLeft,top=clip.top+p.clientTop;if(r.bottom<=top||r.top>=top+p.clientHeight||r.right<=left||r.left>=left+p.clientWidth){visible=false;break}}}
   if(!visible)continue
   if(el.classList.contains('frame-wrap')&&el.dataset.frame.endsWith('Description')){const text=el.querySelector('span');if(text&&text.getBoundingClientRect().height>r.height+.6)throw Error('Clipped description: '+el.dataset.frame)}
   boxes[el.dataset.frame]={x:r.x-origin.x,y:r.y-origin.y,width:r.width,height:r.height}
   const css=getComputedStyle(el);styles[el.dataset.frame]={fontSize:parseFloat(css.fontSize),weight:Number(css.fontWeight),color:color(css.color)}
   if(el.classList.contains('frame-box')){const value=color(css.backgroundColor);fills[el.dataset.frame]={color:value,alpha:ctx.getImageData(0,0,1,1).data[3]/255,radius:parseFloat(css.borderTopLeftRadius),bottomRightRadius:parseFloat(css.borderBottomRightRadius)}}
  }
  return {boxes,styles,fills,origin:{x:origin.x,y:origin.y}}
 },exclude)
}
export async function compareSurface(page,root,actual,expected,label){
 for(const id of expected.frameIds||[])assert(actual.boxes[id],label+' missing Vue control '+id)
 let rectangles=0,styles=0,interiors=0
 for(const [id,box] of Object.entries(actual.boxes)){
  const native=expected.boxes[id];assert(native,label+' missing QML control '+id)
  for(const key of ['x','y','width','height'])assert(Math.abs(box[key]-native[key])<=.1,JSON.stringify({label,id,key,vue:box[key],qml:native[key]}))
  rectangles++
  if(expected.fills?.[id]){
   const fill=actual.fills[id],native=expected.fills[id];assert(fill,label+' '+id+' missing fill')
   for(let index=1;index<7;index+=2)assert(Math.abs(parseInt(fill.color.slice(index,index+2),16)-parseInt(native.color.slice(index,index+2),16))<=1,label+' '+id+' background '+fill.color+' / '+native.color)
   assert(Math.abs(fill.alpha-native.alpha)<.01,label+' '+id+' alpha')
   for(const key of ['radius','bottomRightRadius']) if(native[key] != null) assert(Math.abs(fill[key]-native[key])<=.1,label+' '+id+' '+key+' '+fill[key]+' / '+native[key])
  }
  if(expected.styles[id]?.color){assert.deepEqual(actual.styles[id],expected.styles[id],label+' '+id+' typography/color');styles++}
  if(expected.interiors[id]){
   const indicator=await page.locator(root).locator('[data-frame="'+id+'"] > .app-checkbox-indicator').last().boundingBox()
   for(const key of ['x','y','width','height'])assert(Math.abs(indicator[key]-(key==='x'||key==='y'?actual.origin[key]:0)-expected.interiors[id][key])<=.6,label+' '+id+' indicator '+key)
   interiors++
  }
 }
 return {rectangles,styles,interiors}
}
