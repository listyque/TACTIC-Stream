import {spawn} from 'node:child_process'
import {mkdir,writeFile,readFile} from 'node:fs/promises'
import {createWriteStream} from 'node:fs'
import {fileURLToPath} from 'node:url'
const root=fileURLToPath(new URL('../../',import.meta.url)),out=root+'tools/frame_admin/output/browser/'
await mkdir(out,{recursive:true})
const screens=['groups','users','security','raw','sidebar','columns','types','naming','graph','graph_editor','layout','shell','rules','deletion']
const start=process.argv[2]?screens.indexOf(process.argv[2]):0
if(start<0)throw new Error('Unknown screen: '+process.argv[2])
const results=start?JSON.parse(await readFile(out+'results.json','utf8')).filter(row=>screens.indexOf(row.screen)<start&&row.status===0):[]
for(const screen of screens.slice(start)){
 const stream=createWriteStream(out+screen+'.log')
 const status=await new Promise(resolve=>{
  const child=spawn(process.execPath,screen==='users'?['tests/frame_groups.mjs','--users']:['tests/frame_'+screen+'.mjs'],{cwd:root+'frontend',env:{...process.env,STREAM_BROWSER_CHANNEL:process.env.STREAM_BROWSER_CHANNEL||'msedge'},stdio:['ignore','pipe','pipe']})
  child.stdout.pipe(stream,{end:false});child.stderr.pipe(stream,{end:false})
  const timer=setTimeout(()=>child.kill(),300000)
  child.on('close',code=>{clearTimeout(timer);stream.end();resolve(code)})
 })
 results.push({screen,status,log:screen+'.log'});console.log(screen,status)
 await writeFile(out+'results.json',JSON.stringify(results,null,2))
 if(status)process.exit(status||1)
}
console.log('Paired native/browser Frame suites passed: '+results.length)
