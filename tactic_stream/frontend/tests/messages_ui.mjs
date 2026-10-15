import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { mkdir, readFile } from 'node:fs/promises'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { chromium } from 'playwright'

const root=fileURLToPath(new URL('..',import.meta.url))
const previewPng=await readFile(new URL('fixtures/messages-attachment.png',import.meta.url))
const html=`<!doctype html><html><body><div id="app"></div><script type="module">
import {createApp,h} from 'vue'
import MessagesView from '/src/features/messages/MessagesView.vue'
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{language:'en',mode:'dark'});initializeAppearance();window.appearance=appearance
createApp({provide:{openHelp(){}},data(){return {clicks:0,ticket:'fixture'}},mounted(){window.host=this},render(){return h('div',[
 h('button',{onClick:()=>this.clicks++},'Workspace action'),
 h(MessagesView,{ref:'messages',ticket:this.ticket,project:'cg',login:'admin'})
])}}).directive('window',windowDirective).mount('#app')
</script></body></html>`
const users=[{login:'admin',displayName:'Admin',initials:'A',avatarColor:'#43796c',avatarUrl:'/tests/fixtures/messages-attachment.png'},{login:'test',displayName:'Test',initials:'T',avatarColor:'#43796c'}]
const permissions=Object.fromEntries(['create','send','upload','rename','members','clear','delete','edit','forward','pin','reaction','delete-message'].map(key=>[key,true]))
const conversations=[{conversationId:'favorites',isPersonalNotes:true,recipients:[],messageCount:2,canClearPersonal:true,canRename:true},{conversationId:'group',title:'Review chat',recipients:['test'],participantCount:2,attachmentCount:0,messageCount:2,canRename:true,canManage:true,canAddMembers:true,canDelete:true}]
const records=[{code:'message1',id:1,login:'admin',message:'Review the lighting',timestamp:new Date(Date.now()-60000).toISOString(),__edit_history__:[{editedBy:'admin',editedAt:'2026-10-13 09:00:00',body:'Initial text'}]}]
for(let index=2;index<=24;index++)records.push({code:'message'+index,id:index,login:'admin',message:'History '+index+'\nSecond line\nThird line',timestamp:new Date(Date.now()-60000+index*1000).toISOString()})
records.at(-1).__attachments__=[{code:'snapshot1',__files__:[{code:'original',file_name:'photo.png',type:'main',st_size:previewPng.length},{code:'web',file_name:'preview.png',type:'web',st_size:previewPng.length}]}]
let server,browser
let historyDelay=0
const requests=[],errors=[],deadline=setTimeout(()=>browser?.close(),55000)
try {
 server=await createServer({root,configFile:false,cacheDir:root+'/node_modules/.vite/messages-ui',plugins:[vue(),{
  name:'messages-ui-fixture',configureServer(server){server.middlewares.use(async(req,res,next)=>{
   if(req.url!=='/messages-test')return next()
   try{res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml(req.url,html))}catch(error){next(error)}
  })}
 }],server:{host:'127.0.0.1',port:0,watch:null}});await server.listen()
 browser=await chromium.launch({headless:true})
 const page=await browser.newPage({viewport:{width:1280,height:900},hasTouch:true});page.setDefaultTimeout(6000)
 page.on('pageerror',error=>errors.push(error.message))
 await page.route('**/admin/**',async route=>{
  const action=route.request().url().split('/').at(-1),payload=route.request().postDataJSON();requests.push({action,payload})
  if(action==='file'){await route.fulfill({contentType:'image/png',body:previewPng});return}
  let result={}
  if(action==='list')result={initialized:true,permissions,canCreateGroup:true,canDeleteMessages:true,conversations}
  if(action==='people')result={users}
  if(action==='history') { result={messages:records.filter(row=>!payload.search_text||row.message.toLowerCase().includes(payload.search_text.toLowerCase())).map(row=>({...row,code:payload.message_code+'_'+row.code})),pinHistory:[{messageId:payload.message_code+'_message1',body:'Review the lighting',pinnedBy:'admin'}]};if(historyDelay)await new Promise(resolve=>setTimeout(resolve,historyDelay)) }
  await route.fulfill({json:{result}})
 })
 await page.goto(server.resolvedUrls.local[0]+'messages-test');await page.waitForFunction(()=>!!window.host)
 await page.evaluate(()=>window.host.$refs.messages.open('group'))
 const main=page.locator('.messages-dialog'),popup=page.locator('.messages-popup > .account-panel:popover-open')
 async function settled(){await popup.waitFor();await page.waitForFunction(()=>getComputedStyle(document.querySelector('.messages-popup > .account-panel:popover-open')).scale==='1')}
 await main.getByRole('button',{name:'Chat members',exact:true}).waitFor()
 await mkdir(root+'/../.screenshots/messages-ui-current',{recursive:true})
 await page.waitForFunction(()=>document.querySelector('.messages-viewport[data-current="true"] .attachment-image img')?.naturalWidth>0)
 await main.locator('.messages-viewport:visible .attachment-image img').evaluate(el=>{window.savedPhoto=el;window.savedPhotoSize={width:el.clientWidth,height:el.clientHeight};window.savedPhotoUrl=el.src})
 await main.locator('.messages-viewport:visible .message-row').first().evaluate(el=>window.savedMessage=el)
 await main.locator('.messages-viewport:visible').evaluate(el=>{el.scrollTop=450;window.savedViewport=el})
 await page.evaluate(()=>new Promise(requestAnimationFrame))
 await main.locator('.messages-viewport:visible .message-author img').first().evaluate(el=>window.savedAvatar=el)
 await main.getByRole('button',{name:'Favorites',exact:true}).click()
 await main.locator('.messages-viewport:visible [data-message-id="favorites_message1"]').waitFor()
 await main.getByRole('button',{name:'Review chat',exact:true}).click()
 await main.locator('.messages-viewport:visible [data-message-id="group_message1"]').waitFor()
 assert(await page.evaluate(()=>window.savedMessage.isConnected&&window.savedMessage===document.querySelector('.messages-viewport[data-current="true"] [data-message-id="group_message1"]')),'Cached conversation keeps its rendered message nodes')
 assert.equal(await main.locator('.messages-viewport:visible').evaluate(el=>el.scrollTop),450,'Cached timeline restores its scroll')
 assert(await page.evaluate(()=>window.savedAvatar===document.querySelector('.messages-viewport[data-current="true"] .message-author img')),'Cached avatars keep their image elements')
 const historyReads=requests.filter(row=>row.action==='history').length
 async function refresh(){
  const loaded=page.waitForResponse(response=>response.url().endsWith('/history'))
  await main.getByRole('button',{name:'Refresh conversations and messages',exact:true}).click();await loaded
  await page.waitForFunction(()=>document.querySelector('.messages-dialog').getAttribute('aria-busy')==='false')
 }
 historyDelay=300
 for(let index=0;index<3;index++) {
  await main.getByRole('button',{name:'Favorites',exact:true}).click()
  await main.getByRole('button',{name:'Review chat',exact:true}).click()
 }
 assert.equal(requests.filter(row=>row.action==='history').length,historyReads,'Unchanged cached chats do not reload history')
 conversations[1].lastTimestamp='2026-10-13 12:00:00'
 await refresh()
 await main.getByRole('button',{name:'Favorites',exact:true}).click()
 conversations[1].lastTimestamp='2026-10-13 12:01:00'
 await refresh()
 const refreshed=page.waitForResponse(response=>response.url().endsWith('/history')&&response.request().postDataJSON()?.message_code==='group')
 refreshed.catch(()=>{})
 await main.getByRole('button',{name:'Review chat',exact:true}).click()
 const frames=await page.evaluate(()=>new Promise(resolve=>{
  const frames=[]
  function sample(){
   const active=document.querySelector('.messages-viewport[data-current="true"]')
   const photo=active?.querySelector('.attachment-image img')
   frames.push({sameViewport:active===window.savedViewport,sameMessage:window.savedMessage.isConnected,samePhoto:photo===window.savedPhoto&&photo?.src===window.savedPhotoUrl,photoWidth:photo?.clientWidth,photoHeight:photo?.clientHeight,rows:active?.querySelectorAll('.message-row').length,scroll:active?.scrollTop,visible:active&&getComputedStyle(active).visibility==='visible',loading:!!document.querySelector('.messages-loading')})
   if(frames.length===12)resolve(frames);else requestAnimationFrame(sample)
  }
  requestAnimationFrame(sample)
 }))
 const photoSize=await page.evaluate(()=>window.savedPhotoSize)
 for(const frame of frames){assert(frame.sameViewport&&frame.sameMessage&&frame.samePhoto&&frame.visible&&!frame.loading&&frame.rows===24,JSON.stringify(frame));assert.equal(frame.scroll,450);assert.equal(frame.photoWidth,photoSize.width);assert.equal(frame.photoHeight,photoSize.height)}
 await refreshed;assert(await page.evaluate(()=>window.savedAvatar===document.querySelector('.messages-viewport[data-current="true"] .message-author img')))
 conversations.push({conversationId:'other',title:'Other chat',recipients:['test'],participantCount:2})
 await refresh()
 const oldHistory=page.waitForResponse(response=>response.url().endsWith('/history')&&response.request().postDataJSON()?.message_code==='other');oldHistory.catch(()=>{})
 await main.getByRole('button',{name:'Other chat',exact:true}).click()
 await main.getByRole('button',{name:'Review chat',exact:true}).click()
 await oldHistory
 assert(await page.evaluate(()=>document.querySelector('.messages-viewport[data-current="true"]')===window.savedViewport),'A stale cold-chat response cannot replace the restored conversation')
 assert.equal(await main.locator('.messages-viewport:visible .message-row').count(),24)
 assert.equal(await main.locator('.messages-loading').count(),0)
 historyDelay=0
 await main.locator('.messages-viewport:visible').screenshot({path:root+'/../.screenshots/messages-ui-current/cached-timeline.png'})
 async function anchored(name,selector){
  const trigger=main.getByRole('button',{name,exact:true});await trigger.click();await settled()
  const panel=page.locator(selector+' > .account-panel'),anchorBox=await trigger.boundingBox(),box=await panel.boundingBox()
  assert(Math.abs(box.y-anchorBox.y-anchorBox.height-4)<1,JSON.stringify({name,box,anchorBox}))
  assert.equal(await page.locator('dialog:modal').count(),0)
  assert.equal(await panel.locator('.app-window-controls').count(),0)
  return panel
 }
 let panel=await anchored('Chat members','.messages-members-window')
 assert.equal((await panel.boundingBox()).width,306);assert.equal((await panel.boundingBox()).height,366)
 assert.equal(await panel.getByRole('button').count(),2)
 await panel.screenshot({path:root+'/../.screenshots/messages-ui-current/members.png'})
 await main.getByRole('button',{name:'Chat members',exact:true}).click();await popup.waitFor({state:'hidden'})
 panel=await anchored('Chat members','.messages-members-window')
 await panel.getByRole('button',{name:'Test',exact:true}).focus();await page.keyboard.press('Escape');await popup.waitFor({state:'hidden'})
 assert(await main.getByRole('button',{name:'Chat members',exact:true}).evaluate(el=>el===document.activeElement))
 panel=await anchored('Chat files','.chat-files-window');assert.equal((await panel.boundingBox()).width,356)
 await page.getByRole('button',{name:'Workspace action',exact:true}).click();assert.equal(await page.evaluate(()=>window.host.clicks),1)
 await popup.waitFor({state:'hidden'})
 const timelineHeight=await main.locator('.messages-timeline-frame').evaluate(el=>el.clientHeight)
 panel=await anchored('Search messages','.messages-search-popup')
 assert(await panel.getByRole('textbox').evaluate(el=>el===document.activeElement),'Search popup focuses its field')
 assert((await panel.boundingBox()).height<120,'Search is a compact popup')
 assert.equal(await main.locator('.messages-timeline-frame').evaluate(el=>el.clientHeight),timelineHeight)
 await panel.getByRole('textbox',{name:'Search messages',exact:true}).fill('lighting')
 const searched=page.waitForResponse(response=>response.url().endsWith('/history')&&response.request().postDataJSON()?.search_text==='lighting')
 await panel.getByRole('textbox',{name:'Search messages',exact:true}).press('Enter');await searched;await popup.waitFor({state:'hidden'})
 assert.equal(await main.locator('.messages-viewport:visible .message-row').count(),1)
 assert.equal(await main.locator('.messages-viewport[data-conversation-id="group"][data-current="false"] .message-row').count(),24,'Search retains the full cached conversation')
 panel=await anchored('Search messages','.messages-search-popup');assert.equal(await panel.getByRole('textbox').inputValue(),'lighting')
 await panel.screenshot({path:root+'/../.screenshots/messages-ui-current/search.png'})
 const cleared=page.waitForResponse(response=>response.url().endsWith('/history')&&response.request().postDataJSON()?.search_text==='')
 await panel.getByRole('button',{name:'Clear search',exact:true}).click();await cleared
 assert(await page.evaluate(()=>window.savedMessage===document.querySelector('.messages-viewport[data-current="true"] [data-message-id="group_message1"]')),'Clearing search restores the original rendered timeline')
 await main.getByRole('button',{name:'New conversation',exact:true}).click();await settled()
 panel=page.locator('.messages-people-window > .account-panel');const box=await panel.boundingBox(),owner=await main.boundingBox()
 assert(Math.abs(box.x+box.width/2-owner.x-owner.width/2)<1);assert(Math.abs(box.y+box.height/2-owner.y-owner.height/2)<1)
 assert.equal(await page.locator('dialog:modal').count(),0);await panel.getByRole('button',{name:'Cancel',exact:true}).click()
 await main.getByLabel('Chat actions',{exact:true}).click()
 await main.locator('.chat-actions > .account-panel').getByRole('button',{name:'Rename chat',exact:true}).click();await popup.waitFor()
 panel=page.locator('.messages-rename-window > .account-panel');await panel.getByRole('textbox',{name:'Chat title',exact:true}).fill('Draft title')
 await page.keyboard.press('Escape');assert.equal(requests.filter(row=>row.action==='rename').length,0,'Dismissing a popup does not save its draft')
 await main.getByLabel('Chat actions',{exact:true}).click()
 await main.locator('.chat-actions > .account-panel').getByRole('button',{name:'Add or remove members',exact:true}).click();await settled()
 assert.equal(await page.locator('dialog:modal').count(),0)
 await popup.getByRole('button',{name:'Cancel',exact:true}).click()
 await main.getByLabel('Chat actions',{exact:true}).click()
 await main.locator('.chat-actions > .account-panel').getByRole('button',{name:'Pin history',exact:true}).click();await settled()
 assert.equal(await page.locator('dialog:modal').count(),0);await popup.getByRole('button').first().focus();await page.keyboard.press('Escape')
 await main.getByRole('button',{name:'Edited',exact:true}).click();await settled()
 assert.equal(await page.locator('dialog:modal').count(),0);await page.mouse.click(4,4);await popup.waitFor({state:'hidden'})
 await main.locator('.messages-viewport:visible').getByLabel('Message actions',{exact:true}).first().click()
 await main.locator('.message-actions > .account-panel').getByRole('button',{name:'Edit message',exact:true}).click()
 const modal=page.locator('.messages-edit-window:modal');await modal.waitFor()
 await modal.getByRole('button',{name:'Cancel',exact:true}).click()
 await main.locator('.messages-viewport:visible').getByLabel('Message actions',{exact:true}).first().click()
 await main.locator('.message-actions > .account-panel').getByRole('button',{name:'Forward',exact:true}).click()
 const forward=page.locator('.messages-forward-window[open]');await forward.waitFor();assert.equal(await page.locator('dialog:modal').count(),0)
 await forward.getByRole('button',{name:'Cancel',exact:true}).click()
 const emoji=main.locator('.message-composer .emoji-picker');await emoji.getByLabel('Insert emoji',{exact:true}).click()
 const grid=emoji.locator('.emoji-grid');await grid.getByRole('button').first().waitFor();await page.evaluate(()=>document.fonts.ready)
 const cell=grid.getByRole('button').first()
 assert.equal(await cell.evaluate(el=>getComputedStyle(el).fontSize),'26px');assert((await cell.boundingBox()).height>=40)
 await emoji.locator('.account-panel').screenshot({path:root+'/../.screenshots/messages-ui-current/emoji-desktop.png'})
 await cell.click();assert(await main.getByRole('textbox',{name:'Write a reply',exact:true}).inputValue())
 await page.evaluate(()=>window.appearance.language='ru')
 await main.getByRole('button',{name:'Искать сообщения',exact:true}).click();await popup.waitFor()
 await popup.screenshot({path:root+'/../.screenshots/messages-ui-current/search-ru.png'})
 await page.keyboard.press('Escape')
 await page.setViewportSize({width:320,height:760})
 await emoji.getByLabel('Вставить эмодзи',{exact:true}).click();await cell.waitFor()
 await page.waitForFunction(()=>getComputedStyle(document.querySelector('.message-composer .emoji-picker > .account-panel')).scale==='1')
 assert.equal(await cell.evaluate(el=>getComputedStyle(el).fontSize),'32px');assert((await cell.boundingBox()).height>=44)
 const mobileBox=await emoji.locator('.account-panel').boundingBox();assert(mobileBox.x>=0&&mobileBox.x+mobileBox.width<=320)
 await emoji.locator('.account-panel').screenshot({path:root+'/../.screenshots/messages-ui-current/emoji-mobile.png'})
 await page.keyboard.press('Escape')
 await main.getByLabel('Действия чата',{exact:true}).click()
 await main.locator('.chat-actions > .account-panel').getByRole('button',{name:'Участники чата',exact:true}).click();await settled()
 const membersBox=await popup.boundingBox();assert(membersBox.x>=0&&membersBox.x+membersBox.width<=320)
 await popup.screenshot({path:root+'/../.screenshots/messages-ui-current/members-mobile.png'})
 await page.evaluate(()=>window.host.$refs.messages.close());await popup.waitFor({state:'hidden'})
 conversations.push(...Array.from({length:13},(_,index)=>({conversationId:'cache'+index,title:'Cached '+index,recipients:['test'],participantCount:2})))
 for(let index=0;index<13;index++)await page.evaluate(id=>window.host.$refs.messages.open(id),'cache'+index)
 assert.equal(await main.locator('.messages-viewport').count(),12,'Retained conversation DOM is bounded by the twelve-chat LRU')
 assert.equal(await page.evaluate(()=>window.savedMessage.isConnected),false,'Evicted conversation elements are released')
 await page.evaluate(()=>window.host.ticket='')
 await page.waitForFunction(()=>document.querySelectorAll('.messages-viewport .message-row').length===0)
 assert.deepEqual(errors,[])
 console.log('PASS real Messages UI: cached DOM/images/scroll, twelve continuous frames during delayed refresh, no redundant history reads, stale response/logout/search guards, popups and desktop/mobile emoji')
} finally {clearTimeout(deadline);await browser?.close();await server?.close()}
